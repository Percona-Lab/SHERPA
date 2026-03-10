"""
PDAA SHERPA Connector — Converts SHERPA votes/comments to CustomerEvidence.

Importance mapping:
  Critical    → urgency=High,   weight=3.0
  Important   → urgency=Medium, weight=2.0
  Nice to have→ urgency=Low,    weight=1.0
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional

from .models import CustomerEvidence

log = logging.getLogger("pdaa.sherpa_connector")

IMPORTANCE_MAP = {
    "critical":      {"urgency": "High",   "weight": 3.0},
    "important":     {"urgency": "Medium", "weight": 2.0},
    "nice_to_have":  {"urgency": "Low",    "weight": 1.0},
    "nice to have":  {"urgency": "Low",    "weight": 1.0},
}


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
        # Notion-specific fields
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
        # Notion-specific fields
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

    from .ingestion import ingest_evidence
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

    from .ingestion import ingest_evidence
    ingest_evidence(evidence)
