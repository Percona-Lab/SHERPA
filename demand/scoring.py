"""
SHERPA Demand Engine — Weighted demand score calculation.

Score formula:
  demand_score = sum(evidence.score_weight * source_multiplier * recency_factor)

Source multipliers reward diverse evidence:
  - Internal (SHERPA votes): 1.0
  - Customer (Jira, support): 1.5
  - Community (forum, Slack): 0.8

Recency: evidence less than 30 days old gets full weight,
older evidence decays linearly to 0.5 at 180 days.
"""

import logging
from datetime import datetime
from typing import List

from .models import CustomerEvidence, DemandSignal

log = logging.getLogger("demand.scoring")

# Importance mapping from SHERPA vote levels to urgency/weight
IMPORTANCE_MAP = {
    "critical":      {"urgency": "High",   "weight": 3.0},
    "important":     {"urgency": "Medium", "weight": 2.0},
    "nice_to_have":  {"urgency": "Low",    "weight": 1.0},
    "nice to have":  {"urgency": "Low",    "weight": 1.0},
}

SOURCE_MULTIPLIERS = {
    "Internal": 1.0,
    "External": 1.5,
    "Community": 0.8,
}

URGENCY_WEIGHTS = {
    "High": 3.0,
    "Medium": 2.0,
    "Low": 1.0,
}


def _recency_factor(timestamp_str: str) -> float:
    """Decay factor based on age. 1.0 if <30 days, linear decay to 0.5 at 180 days."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age_days = (datetime.now(ts.tzinfo) - ts).days
    except (ValueError, TypeError):
        return 0.75  # unknown age gets moderate weight

    if age_days <= 30:
        return 1.0
    if age_days >= 180:
        return 0.5
    return 1.0 - 0.5 * ((age_days - 30) / 150)


def calculate_demand_score(signal: DemandSignal) -> float:
    """Calculate the aggregate demand score for a signal from all its evidence."""
    if not signal.evidence:
        return 0.0

    total = 0.0
    for ev in signal.evidence:
        source_mult = SOURCE_MULTIPLIERS.get(ev.source_type, 1.0)
        recency = _recency_factor(ev.timestamp)
        total += ev.score_weight * source_mult * recency

    return round(total, 2)


def recalculate(signal: DemandSignal) -> DemandSignal:
    """Recalculate and update the demand score on a signal."""
    signal.demand_score = calculate_demand_score(signal)
    signal.updated_at = datetime.utcnow().isoformat() + "Z"
    return signal
