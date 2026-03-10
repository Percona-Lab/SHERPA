"""
PDAA Ingestion Pipeline — Extract → Classify → Match → Store.

This is the main entry point for processing evidence from any source.
"""

import hashlib
import logging
from datetime import datetime
from typing import Union

from .models import CustomerEvidence, DemandSignal
from .matching import find_best_match, should_auto_merge
from .scoring import recalculate
from .git_sync import GitSyncManager
from .slack_notify import notify_new_signal, notify_evidence_added

log = logging.getLogger("pdaa.ingestion")


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
        notify_new_signal(new_signal, evidence)
        return new_signal
