"""
SHERPA Demand Engine — aggregates demand signals from votes,
comments, Jira, Slack, and forums into a scored, Git-backed store.
"""

from .models import DemandSignal, CustomerEvidence
from .ingestion import ingest_evidence, handle_vote_event, handle_comment_event
from . import notion_sync

__all__ = [
    "DemandSignal",
    "CustomerEvidence",
    "ingest_evidence",
    "handle_vote_event",
    "handle_comment_event",
    "notion_sync",
]
