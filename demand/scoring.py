"""
SHERPA Demand Engine — Discovery-informed dual scoring.

Implements Gilad/Cagan principles:
- Dual scoring: Business Impact (MRR, deal blockers, churn) + User Value
  (community, surveys, call transcripts) instead of one opaque number
- Source diversity rewards evidence corroborated across multiple source types
- Confidence levels (Strong/Moderate/Weak) based on evidence quality
- Anti-SCORE warnings flag sparse, single-source, or stale signals

Combined formula:
  demand_score = profile.business * business_impact
               + profile.user_value * user_value
               + profile.internal * internal_vote_score

Profiles let PMs shift the lens (Revenue Focused, Community Driven, etc.)
without hiding the underlying component scores.
"""

import logging
import math
from datetime import datetime, timezone
from typing import List, Set

from .models import CustomerEvidence, DemandSignal

log = logging.getLogger("demand.scoring")

# ─── Importance mapping from SHERPA vote levels ───

IMPORTANCE_MAP = {
    "critical":      {"urgency": "High",   "weight": 3.0},
    "important":     {"urgency": "Medium", "weight": 2.0},
    "nice_to_have":  {"urgency": "Low",    "weight": 1.0},
    "nice to have":  {"urgency": "Low",    "weight": 1.0},
}

# ─── Source classification ───
# Maps evidence source names to scoring categories

BUSINESS_SOURCES = {
    "Salesforce", "TAM Notes", "SDM Notes",
    "SE Feature Requests", "SE Prospect Requests",
    "ServiceNow", "6sense",
}

USER_VALUE_SOURCES = {
    "Percona Forums", "GitHub", "Product Surveys",
    "Update.AI", "Zoom",
}

INTERNAL_SOURCES = {"SHERPA"}

# Sources where evidence counts as "customer" (has ACV/MRR context)
CUSTOMER_EVIDENCE_SOURCES = {
    "Salesforce", "TAM Notes", "SDM Notes",
    "SE Feature Requests", "SE Prospect Requests",
    "ServiceNow",
}

# Sources where evidence counts as "community"
COMMUNITY_EVIDENCE_SOURCES = {
    "Percona Forums", "GitHub", "Product Surveys",
}

# ─── Weight profiles ───
# PMs switch profiles to shift the scoring lens without hiding component scores

WEIGHT_PROFILES = {
    "balanced": {"business": 0.50, "user_value": 0.30, "internal": 0.20},
    "revenue_focused": {"business": 0.70, "user_value": 0.15, "internal": 0.15},
    "community_driven": {"business": 0.20, "user_value": 0.60, "internal": 0.20},
    "strategic_bet": {"business": 0.40, "user_value": 0.40, "internal": 0.20},
}

DEFAULT_PROFILE = "balanced"

# ─── Confidence thresholds ───

CONFIDENCE_STRONG_MIN_EVIDENCE = 5
CONFIDENCE_STRONG_MIN_SOURCES = 3
CONFIDENCE_MODERATE_MIN_EVIDENCE = 3
CONFIDENCE_MODERATE_MIN_SOURCES = 2
STALE_THRESHOLD_DAYS = 90


# ─── Recency ───

def _recency_factor(timestamp_str: str) -> float:
    """Decay factor based on age. 1.0 if <30 days, linear decay to 0.5 at 180 days."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - ts).days
    except (ValueError, TypeError):
        return 0.75  # unknown age gets moderate weight

    if age_days <= 30:
        return 1.0
    if age_days >= 180:
        return 0.5
    return 1.0 - 0.5 * ((age_days - 30) / 150)


def _days_since(timestamp_str: str) -> int:
    """Return days since a timestamp, or 999 if unparseable."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).days
    except (ValueError, TypeError):
        return 999


# ─── Business Impact Score (0-100) ───
# Components: Customer MRR (40%), Deal Blockers (30%), Churn Risk (20%), Recency (10%)

def _business_impact_score(evidence: List[CustomerEvidence]) -> float:
    biz_evidence = [e for e in evidence if e.source in BUSINESS_SOURCES]
    if not biz_evidence:
        return 0.0

    # Customer MRR (40%) — log-scaled sum of MRR values
    total_mrr = sum(e.mrr or 0.0 for e in biz_evidence)
    mrr_component = min(math.log1p(total_mrr) / math.log1p(500_000) * 100, 100) if total_mrr > 0 else 0.0

    # Deal Blockers (30%) — count of deal-blocker evidence
    deal_blockers = sum(1 for e in biz_evidence if e.urgency == "High" and "blocker" in (e.description or "").lower())
    blocker_component = min(deal_blockers * 25, 100)

    # Churn Risk (20%) — evidence tagged as churn/negative sentiment
    churn_signals = sum(1 for e in biz_evidence if e.sentiment in ("Churn Signal", "Negative"))
    churn_component = min(churn_signals * 33, 100)

    # Recency (10%) — most recent business evidence
    recency_vals = [_recency_factor(e.timestamp) for e in biz_evidence]
    recency_component = max(recency_vals) * 100 if recency_vals else 0.0

    return round(
        mrr_component * 0.40
        + blocker_component * 0.30
        + churn_component * 0.20
        + recency_component * 0.10,
        2,
    )


# ─── User Value Score (0-100) ───
# Components: Community Volume (35%), Surveys (25%), Call Transcripts (25%), Recency (15%)

def _user_value_score(evidence: List[CustomerEvidence]) -> float:
    uv_evidence = [e for e in evidence if e.source in USER_VALUE_SOURCES]
    if not uv_evidence:
        return 0.0

    # Community Volume (35%) — forum + GitHub count, caps at 50
    community_count = sum(1 for e in uv_evidence if e.source in ("Percona Forums", "GitHub"))
    community_component = min(community_count / 50 * 100, 100)

    # Survey Mentions (25%)
    survey_count = sum(1 for e in uv_evidence if e.source == "Product Surveys")
    survey_component = min(survey_count / 20 * 100, 100)

    # Call Transcripts (25%) — Update.AI + Zoom
    call_count = sum(1 for e in uv_evidence if e.source in ("Update.AI", "Zoom"))
    call_component = min(call_count / 15 * 100, 100)

    # Recency (15%)
    recency_vals = [_recency_factor(e.timestamp) for e in uv_evidence]
    recency_component = max(recency_vals) * 100 if recency_vals else 0.0

    return round(
        community_component * 0.35
        + survey_component * 0.25
        + call_component * 0.25
        + recency_component * 0.15,
        2,
    )


# ─── Internal Vote Score (0-100) ───

def _internal_vote_score(evidence: List[CustomerEvidence]) -> float:
    internal = [e for e in evidence if e.source in INTERNAL_SOURCES]
    if not internal:
        return 0.0

    weighted_sum = sum(e.score_weight * _recency_factor(e.timestamp) for e in internal)
    # Normalize: 10 critical votes (weight 3.0 each) = 100
    return round(min(weighted_sum / 30 * 100, 100), 2)


# ─── Source Diversity ───

def _source_diversity(evidence: List[CustomerEvidence]) -> int:
    """Count distinct source types (not individual sources)."""
    source_types: Set[str] = set()
    for e in evidence:
        if e.source in BUSINESS_SOURCES:
            source_types.add("business")
        elif e.source in USER_VALUE_SOURCES:
            source_types.add("user_value")
        elif e.source in INTERNAL_SOURCES:
            source_types.add("internal")
        else:
            source_types.add(e.source)  # unknown sources count individually
    return len(source_types)


# ─── Confidence Level ───

def _confidence_level(evidence: List[CustomerEvidence], source_diversity: int) -> str:
    count = len(evidence)
    if count >= CONFIDENCE_STRONG_MIN_EVIDENCE and source_diversity >= CONFIDENCE_STRONG_MIN_SOURCES:
        return "Strong"
    if count >= CONFIDENCE_MODERATE_MIN_EVIDENCE and source_diversity >= CONFIDENCE_MODERATE_MIN_SOURCES:
        return "Moderate"
    return "Weak"


# ─── Anti-SCORE Warnings ───

def _evidence_warnings(signal: DemandSignal) -> List[str]:
    """Generate warnings that flag potential SCORE-method decision-making.

    These warnings make it impossible to silently prioritize a signal
    on sparse, single-source, or stale evidence (Gilad's "must-have" bypass).
    """
    warnings = []
    evidence = signal.evidence

    if len(evidence) < 3:
        warnings.append("Sparse Evidence")

    unique_sources = {e.source for e in evidence}
    if len(unique_sources) <= 1:
        warnings.append("Single Source")

    # Stale: no evidence in 90+ days
    if evidence:
        most_recent = min(_days_since(e.timestamp) for e in evidence)
        if most_recent >= STALE_THRESHOLD_DAYS:
            warnings.append("Stale Data")

    # No customer data (no business case)
    has_customer = any(e.source in CUSTOMER_EVIDENCE_SOURCES for e in evidence)
    if not has_customer:
        warnings.append("No Customer Data")

    # No community data (may not affect broader user base)
    has_community = any(e.source in COMMUNITY_EVIDENCE_SOURCES for e in evidence)
    if not has_community:
        warnings.append("No Community Data")

    # Contradictory signals (mixed sentiment)
    sentiments = {e.sentiment for e in evidence if e.sentiment and e.sentiment != "Neutral"}
    if len(sentiments) > 1:
        warnings.append("Contradictory Signals")

    return warnings


# ─── Combined Demand Score ───

def calculate_demand_score(signal: DemandSignal, profile: str = DEFAULT_PROFILE) -> float:
    """Calculate composite demand score from dual sub-scores.

    demand_score = business_weight * business_impact
                 + user_value_weight * user_value
                 + internal_weight * internal_votes
    """
    weights = WEIGHT_PROFILES.get(profile, WEIGHT_PROFILES[DEFAULT_PROFILE])

    biz = signal.business_impact_score
    uv = signal.user_value_score
    internal = _internal_vote_score(signal.evidence)

    return round(
        weights["business"] * biz
        + weights["user_value"] * uv
        + weights["internal"] * internal,
        2,
    )


# ─── Main recalculate entry point ───

def recalculate(signal: DemandSignal, profile: str = DEFAULT_PROFILE) -> DemandSignal:
    """Recalculate all scores, confidence, diversity, and warnings on a signal."""
    # Sub-scores
    signal.business_impact_score = _business_impact_score(signal.evidence)
    signal.user_value_score = _user_value_score(signal.evidence)

    # Source diversity and confidence
    signal.source_diversity = _source_diversity(signal.evidence)
    signal.confidence_level = _confidence_level(signal.evidence, signal.source_diversity)

    # Anti-SCORE warnings
    signal.evidence_warnings = _evidence_warnings(signal)

    # Aggregate counts for Notion
    signal.customer_count = sum(
        1 for e in signal.evidence if e.source in CUSTOMER_EVIDENCE_SOURCES
    )
    signal.community_mentions = sum(
        1 for e in signal.evidence if e.source in COMMUNITY_EVIDENCE_SOURCES
    )
    signal.total_mrr = sum(e.mrr or 0.0 for e in signal.evidence)

    # Combined score
    signal.demand_score = calculate_demand_score(signal, profile)

    signal.updated_at = datetime.utcnow().isoformat() + "Z"
    return signal
