"""
SHERPA Demand Engine — DemandSignal and CustomerEvidence dataclasses.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class CustomerEvidence:
    """A single piece of evidence supporting a demand signal."""
    id: str
    source: str                     # "SHERPA", "Slack", "Jira", "Percona Forums", etc.
    source_type: str                # "Internal", "External"
    title: str
    description: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    urgency: str = "Medium"         # "High", "Medium", "Low"
    confidence: float = 0.8
    score_weight: float = 1.0
    timestamp: str = ""
    raw_data: dict = field(default_factory=dict)

    # Notion-specific fields for Customer Evidence DB
    summary: str = ""               # Title property in Notion
    evidence_type: str = "Internal" # "Customer", "Community", "Market", "Internal"
    confidence_label: str = "Medium"  # "High", "Medium", "Low" — string for Notion select
    ingested_by: str = "Agent - Scheduled"  # "Agent - Scheduled", "Agent - Manual", "PM - Direct"
    mrr: Optional[float] = None
    account_name: str = ""
    contact: str = ""
    verbatim: str = ""
    source_url: Optional[str] = None
    sentiment: str = "Neutral"      # "Positive", "Neutral", "Negative", "Churn Signal"
    product_line: str = ""
    date_captured: str = ""
    notion_page_id: Optional[str] = None  # Notion page ID once synced

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if not self.summary:
            self.summary = self.title
        if not self.date_captured:
            self.date_captured = datetime.utcnow().strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CustomerEvidence":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DemandSignal:
    """An aggregated demand signal with evidence from multiple sources."""
    id: str
    title: str
    description: str
    category: str = "Feature Request"   # "Feature Request", "Pain Point", "Bug", "Use Case", "Integration"
    status: str = "New"                 # "New", "Reviewing", "Accepted", "Declined"
    demand_score: float = 0.0
    evidence: List[CustomerEvidence] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    notion_url: Optional[str] = None
    feature_id: Optional[str] = None

    # Notion-specific fields for Demand Signals DB
    impact_score: Optional[float] = None
    product_line: str = ""
    urgency: str = "Medium"             # "Churn Risk", "Deal Blocker", "High", "Medium", "Low"
    sources: List[str] = field(default_factory=list)  # ["SHERPA", "Slack", "Jira"]
    total_mrr: Optional[float] = None
    customer_count: int = 0
    community_mentions: int = 0
    strategic_alignment: str = ""       # "Core", "Adjacent", "Transformational", "Not Aligned"
    frequency: str = ""                 # "Daily", "Weekly", "Monthly", "Quarterly", "One-off"
    first_reported: str = ""
    last_activity: str = ""
    git_sha: str = ""
    product_area: str = ""
    jira_url: Optional[str] = None
    notion_page_id: Optional[str] = None  # Notion page ID once synced

    def __post_init__(self):
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.first_reported:
            self.first_reported = datetime.utcnow().strftime("%Y-%m-%d")
        if not self.last_activity:
            self.last_activity = datetime.utcnow().strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DemandSignal":
        evidence_data = data.pop("evidence", [])
        signal = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        signal.evidence = [CustomerEvidence.from_dict(e) for e in evidence_data]
        return signal

    def add_evidence(self, evidence: CustomerEvidence):
        self.evidence.append(evidence)
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        self.last_activity = datetime.utcnow().strftime("%Y-%m-%d")
        # Track unique sources
        if evidence.source and evidence.source not in self.sources:
            self.sources.append(evidence.source)

    @staticmethod
    def generate_id(title: str) -> str:
        normalized = title.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]
