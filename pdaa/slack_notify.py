"""
PDAA Slack Notifications — Block Kit formatters for #pdaa-signals.
"""

import logging
import os
from typing import Optional

import requests

from .models import DemandSignal, CustomerEvidence

log = logging.getLogger("pdaa.slack_notify")

SLACK_WEBHOOK_URL = os.environ.get("PDAA_SLACK_WEBHOOK_URL", "")


def _source_badge(source: str) -> str:
    """Emoji badge by evidence source."""
    badges = {
        "sherpa_vote": "\U0001f3d4\ufe0f SHERPA",   # 🏔️
        "sherpa_comment": "\U0001f3d4\ufe0f SHERPA",
        "jira": "\U0001f41b Jira",
        "slack": "\U0001f4ac Slack",
        "forum": "\U0001f310 Forum",
    }
    return badges.get(source, f"\U0001f4e5 {source}")


def _urgency_emoji(urgency: str) -> str:
    if urgency == "High":
        return "\U0001f534"   # 🔴
    if urgency == "Medium":
        return "\U0001f7e0"   # 🟠
    return "\U0001f7e2"       # 🟢


def format_new_signal(signal: DemandSignal, evidence: CustomerEvidence) -> dict:
    """Block Kit payload for a new demand signal."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"\U0001f4e1 New Demand Signal", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{signal.title}*\n"
                        f"{_source_badge(evidence.source)} | "
                        f"{_urgency_emoji(evidence.urgency)} {evidence.urgency} urgency\n"
                        f"Score: *{signal.demand_score}*"
                    ),
                },
            },
            {"type": "divider"},
        ]
    }


def format_evidence_added(signal: DemandSignal, evidence: CustomerEvidence) -> dict:
    """Block Kit payload for new evidence on an existing signal."""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"\U0001f4ca Evidence Added", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{signal.title}*\n"
                        f"{_source_badge(evidence.source)} | "
                        f"{_urgency_emoji(evidence.urgency)} {evidence.urgency}\n"
                        f"Total evidence: *{len(signal.evidence)}* | "
                        f"Score: *{signal.demand_score}*"
                    ),
                },
            },
            {"type": "divider"},
        ]
    }


def notify(payload: dict) -> bool:
    """Post a Block Kit payload to the configured Slack webhook. Returns success."""
    if not SLACK_WEBHOOK_URL:
        log.debug("PDAA_SLACK_WEBHOOK_URL not set, skipping notification")
        return False
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return True
    except Exception as e:
        log.warning(f"Slack notification failed: {e}")
        return False


def notify_new_signal(signal: DemandSignal, evidence: CustomerEvidence):
    return notify(format_new_signal(signal, evidence))


def notify_evidence_added(signal: DemandSignal, evidence: CustomerEvidence):
    return notify(format_evidence_added(signal, evidence))
