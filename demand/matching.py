"""
SHERPA Demand Engine — Semantic match (LLM) with keyword fallback.

When SHERPA_LLM_ENDPOINT is set, uses an LLM to compare evidence titles
against existing demand signals. Otherwise, falls back to keyword overlap.
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


def llm_similarity(evidence_title: str, signal_title: str) -> Optional[float]:
    """Use LLM endpoint for semantic similarity. Returns None if unavailable."""
    if not LLM_ENDPOINT:
        return None
    try:
        resp = requests.post(
            LLM_ENDPOINT,
            json={
                "task": "similarity",
                "text_a": evidence_title,
                "text_b": signal_title,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return float(resp.json().get("score", 0.0))
    except Exception as e:
        log.debug(f"LLM similarity failed, falling back to keyword: {e}")
        return None


def find_best_match(
    title: str,
    signals: List[DemandSignal],
) -> Tuple[Optional[DemandSignal], float]:
    """Find the best matching demand signal for a given title.

    Returns (matched_signal, confidence). If no match meets the threshold,
    returns (None, 0.0).
    """
    if not signals:
        return None, 0.0

    best_signal = None
    best_score = 0.0

    for signal in signals:
        # Try LLM first, fall back to keyword
        score = llm_similarity(title, signal.title)
        if score is None:
            score = keyword_similarity(title, signal.title)

        if score > best_score:
            best_score = score
            best_signal = signal

    if best_score >= MATCH_THRESHOLD:
        return best_signal, best_score

    return None, 0.0


def should_auto_merge(confidence: float) -> bool:
    """Confidence >= 0.90 means auto-merge; 0.75-0.90 means flag for review."""
    return confidence >= AUTO_MERGE_THRESHOLD
