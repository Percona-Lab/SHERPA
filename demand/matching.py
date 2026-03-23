"""
SHERPA Demand Engine — Problem-level matching (LLM) with keyword fallback.

Discovery-informed: matches evidence to existing signals at the PROBLEM level,
not the feature level. "Add read replicas to operators" and "Operator deployments
can't scale reads" should match the same underlying demand signal.

When SHERPA_LLM_ENDPOINT is set, uses an LLM to compare the underlying need
in new evidence against existing signals' problem statements. Otherwise, falls
back to keyword overlap on titles.
"""

import logging
import os
import re
from typing import List, Optional, Tuple

import requests

from .models import DemandSignal

log = logging.getLogger("demand.matching")

LLM_ENDPOINT = os.environ.get("SHERPA_LLM_ENDPOINT", "")
MATCH_THRESHOLD = 0.75
AUTO_MERGE_THRESHOLD = 0.90


def _normalize(text: str) -> set:
    """Lowercase, strip punctuation, split into token set."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    # Remove common stop words
    stop = {"the", "a", "an", "is", "to", "for", "and", "of", "in", "on", "with", "as"}
    return {t for t in tokens if t not in stop and len(t) > 1}


def keyword_similarity(a: str, b: str) -> float:
    """Jaccard similarity on normalized token sets."""
    tokens_a = _normalize(a)
    tokens_b = _normalize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def llm_problem_match(evidence_text: str, signal: DemandSignal) -> Optional[float]:
    """Use LLM to determine if new evidence describes the same underlying problem.

    Compares against both the signal's problem_statement (if set) and title,
    asking the LLM to look past surface feature requests to the root need.
    """
    if not LLM_ENDPOINT:
        return None

    compare_to = signal.problem_statement or signal.title
    try:
        resp = requests.post(
            LLM_ENDPOINT,
            json={
                "task": "problem_match",
                "instructions": (
                    "Compare these two texts. Ignore surface-level feature request wording. "
                    "Score 0.0-1.0 based on whether they describe the SAME underlying "
                    "customer problem or need. Two different feature requests that solve "
                    "the same problem should score high."
                ),
                "text_a": evidence_text,
                "text_b": compare_to,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return float(resp.json().get("score", 0.0))
    except Exception as e:
        log.debug(f"LLM problem match failed, falling back to keyword: {e}")
        return None


def extract_problem_statement(evidence_title: str, evidence_description: str) -> Optional[str]:
    """Use LLM to extract the underlying problem/need from a feature request.

    Returns the problem statement, or None if LLM is unavailable.
    """
    if not LLM_ENDPOINT:
        return None
    try:
        resp = requests.post(
            LLM_ENDPOINT,
            json={
                "task": "extract_problem",
                "instructions": (
                    "Extract the underlying customer PROBLEM or NEED from this evidence. "
                    "Strip away the specific solution/feature request and state the core "
                    "problem in one sentence. Example: 'Add read replicas to operators' → "
                    "'Database operator deployments cannot scale read-heavy workloads.'"
                ),
                "title": evidence_title,
                "description": evidence_description,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("problem_statement")
    except Exception as e:
        log.debug(f"LLM problem extraction failed: {e}")
        return None


def find_best_match(
    title: str,
    signals: List[DemandSignal],
    description: str = "",
) -> Tuple[Optional[DemandSignal], float]:
    """Find the best matching demand signal for new evidence.

    Uses problem-level matching: compares the underlying need, not just
    surface feature request wording. Falls back to keyword similarity
    on titles when LLM is unavailable.

    Returns (matched_signal, confidence). If no match meets the threshold,
    returns (None, 0.0).
    """
    if not signals:
        return None, 0.0

    evidence_text = f"{title}. {description}".strip() if description else title
    best_signal = None
    best_score = 0.0

    for signal in signals:
        # Try LLM problem-level match first
        score = llm_problem_match(evidence_text, signal)
        if score is None:
            # Fallback: keyword similarity against both title and problem_statement
            title_score = keyword_similarity(title, signal.title)
            problem_score = (
                keyword_similarity(title, signal.problem_statement)
                if signal.problem_statement
                else 0.0
            )
            score = max(title_score, problem_score)

        if score > best_score:
            best_score = score
            best_signal = signal

    if best_score >= MATCH_THRESHOLD:
        return best_signal, best_score

    return None, 0.0


def should_auto_merge(confidence: float) -> bool:
    """Confidence >= 0.90 means auto-merge; 0.75-0.90 means flag for review."""
    return confidence >= AUTO_MERGE_THRESHOLD
