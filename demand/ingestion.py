"""
SHERPA Demand Engine — Extract → Classify → Match → Store.

This is the main entry point for processing evidence from any source.
Also contains converters for SHERPA votes/comments → CustomerEvidence.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, Union

from .models import CustomerEvidence, DemandSignal
from .matching import find_best_match, should_auto_merge
from .scoring import recalculate, IMPORTANCE_MAP
from .git_sync import GitSyncManager
from .slack_notify import notify_new_signal, notify_evidence_added

log = logging.getLogger("demand.ingestion")


# ─── SHERPA Vote/Comment → Evidence Converters ───

def _evidence_id(prefix: str, feature_id: str, email: str) -> str:
    raw = f"{prefix}-{feature_id}-{email}-{datetime.utcnow().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def sherpa_vote_to_evidence(
    feature_id: str,
    feature_title: str,
    voter_email: str,
    importance: str,
    tallies: dict,
) -> CustomerEvidence:
    """Convert a SHERPA vote into a CustomerEvidence object."""
    mapping = IMPORTANCE_MAP.get(importance.lower(), {"urgency": "Medium", "weight": 2.0})

    return CustomerEvidence(
        id=_evidence_id("vote", feature_id, voter_email),
        source="SHERPA",
        source_type="Internal",
        title=feature_title,
        description=f"Internal vote ({importance}) from {voter_email}",
        customer_email=voter_email,
        urgency=mapping["urgency"],
        confidence=0.95,
        score_weight=mapping["weight"],
        raw_data={
            "feature_id": feature_id,
            "importance": importance,
            "tallies": tallies,
            "notion_url": f"https://www.notion.so/{feature_id.replace('-', '')}",
        },
        summary=f"SHERPA vote: {feature_title} ({importance})",
        evidence_type="Internal",
        confidence_label="High",
        ingested_by="Agent - Scheduled",
        contact=voter_email,
        verbatim=f"Voted '{importance}' on feature: {feature_title}",
        sentiment="Positive",
    )


def sherpa_comment_to_evidence(
    feature_id: str,
    feature_title: str,
    voter_email: str,
    comment_text: str,
    tallies: dict,
) -> CustomerEvidence:
    """Convert a SHERPA comment into a CustomerEvidence object."""
    return CustomerEvidence(
        id=_evidence_id("comment", feature_id, voter_email),
        source="SHERPA",
        source_type="Internal",
        title=feature_title,
        description=comment_text,
        customer_email=voter_email,
        urgency="Medium",
        confidence=0.85,
        score_weight=1.5,
        raw_data={
            "feature_id": feature_id,
            "comment": comment_text,
            "tallies": tallies,
            "notion_url": f"https://www.notion.so/{feature_id.replace('-', '')}",
        },
        summary=f"SHERPA comment: {feature_title}",
        evidence_type="Internal",
        confidence_label="High",
        ingested_by="Agent - Scheduled",
        contact=voter_email,
        verbatim=comment_text[:2000],
        sentiment="Positive",
    )


def handle_vote_event(
    feature_id: str,
    feature_title: str,
    voter_email: str,
    voter_display_name: Optional[str],
    importance: str,
    tallies: dict,
    notion_url: str,
) -> None:
    """Called directly from SHERPA vote handler. No HTTP involved."""
    evidence = sherpa_vote_to_evidence(
        feature_id=feature_id,
        feature_title=feature_title,
        voter_email=voter_email,
        importance=importance,
        tallies=tallies,
    )
    if notion_url:
        evidence.raw_data["notion_url"] = notion_url
        evidence.source_url = notion_url
    if voter_display_name:
        evidence.customer_name = voter_display_name
        evidence.contact = voter_display_name

    ingest_evidence(evidence)


def handle_comment_event(
    feature_id: str,
    feature_title: str,
    voter_email: str,
    voter_display_name: Optional[str],
    comment_text: str,
    tallies: dict,
    notion_url: str,
) -> None:
    """Called directly from SHERPA comment handler. No HTTP involved."""
    evidence = sherpa_comment_to_evidence(
        feature_id=feature_id,
        feature_title=feature_title,
        voter_email=voter_email,
        comment_text=comment_text,
        tallies=tallies,
    )
    if notion_url:
        evidence.raw_data["notion_url"] = notion_url
        evidence.source_url = notion_url
    if voter_display_name:
        evidence.customer_name = voter_display_name
        evidence.contact = voter_display_name

    ingest_evidence(evidence)


# ─── Main Ingestion Pipeline ───

def ingest_evidence(data: Union[dict, CustomerEvidence]) -> DemandSignal:
    """Main pipeline: takes raw evidence data, matches or creates a signal, stores and notifies.

    Args:
        data: Either a CustomerEvidence object or a dict with evidence fields.
              Dict must include at minimum: title, source, description.

    Returns:
        The DemandSignal that was created or updated.
    """
    # Normalize input
    if isinstance(data, dict):
        if "id" not in data:
            raw = f"{data.get('title', '')}-{data.get('source', '')}-{datetime.utcnow().isoformat()}"
            data["id"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        evidence = CustomerEvidence.from_dict(data)
    else:
        evidence = data

    manager = GitSyncManager()
    existing_signals = manager.load_all_signals()

    # Match against existing signals
    matched_signal, confidence = find_best_match(evidence.title, existing_signals)

    if matched_signal and confidence > 0:
        # Append evidence to existing signal
        matched_signal.add_evidence(evidence)
        recalculate(matched_signal)

        if should_auto_merge(confidence):
            log.info(f"Auto-merged evidence into signal '{matched_signal.title}' (confidence={confidence:.2f})")
        else:
            matched_signal.status = "Reviewing"
            log.info(f"Evidence added to '{matched_signal.title}' for review (confidence={confidence:.2f})")

        manager.save_signal(matched_signal)

        # Notion sync (non-blocking)
        try:
            from .notion_sync import upsert_demand_signal, create_evidence
            signal_page_id = upsert_demand_signal(matched_signal)
            if signal_page_id:
                create_evidence(evidence, signal_page_id=signal_page_id)
        except Exception as e:
            log.warning(f"Notion sync failed (non-blocking): {e}")

        notify_evidence_added(matched_signal, evidence)
        return matched_signal
    else:
        # Create new demand signal
        signal_id = DemandSignal.generate_id(evidence.title)
        new_signal = DemandSignal(
            id=signal_id,
            title=evidence.title,
            description=evidence.description,
            feature_id=evidence.raw_data.get("feature_id"),
            notion_url=evidence.raw_data.get("notion_url"),
        )
        new_signal.add_evidence(evidence)
        recalculate(new_signal)

        log.info(f"Created new demand signal '{new_signal.title}' (score={new_signal.demand_score})")

        manager.save_signal(new_signal)

        # Notion sync (non-blocking)
        try:
            from .notion_sync import upsert_demand_signal, create_evidence
            signal_page_id = upsert_demand_signal(new_signal)
            if signal_page_id:
                create_evidence(evidence, signal_page_id=signal_page_id)
        except Exception as e:
            log.warning(f"Notion sync failed (non-blocking): {e}")

        notify_new_signal(new_signal, evidence)
        return new_signal
