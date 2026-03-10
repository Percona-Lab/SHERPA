"""
PDAA Data Models — DemandSignal and CustomerEvidence dataclasses.
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
    source: str                     # "sherpa_vote", "sherpa_comment", "jira", "slack", "forum"
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

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

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
    category: str = "Feature Request"
    status: str = "New"             # "New", "Reviewing", "Accepted", "Declined"
    demand_score: float = 0.0
    evidence: List[CustomerEvidence] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    notion_url: Optional[str] = None
    feature_id: Optional[str] = None

    def __post_init__(self):
        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

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

    @staticmethod
    def generate_id(title: str) -> str:
        normalized = title.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]
