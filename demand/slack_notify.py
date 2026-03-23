"""
SHERPA Demand Engine — Slack notifications for #sherpa-signals.
"""

import logging
import os
from typing import Optional

import requests

from .models import DemandSignal, CustomerEvidence

log = logging.getLogger("demand.slack_notify")

SLACK_WEBHOOK_URL = os.environ.get("SHERPA_SLACK_WEBHOOK_URL", "")


def _source_badge(source: str) -> str:
    """Emoji badge by evidence source."""
    badges = {
        "SHERPA": "\U0001f5f3\ufe0f SHERPA",     # 🗳️
        "sherpa_vote": "\U0001f5f3\ufe0f SHERPA",
        "sherpa_comment": "\U0001f5f3\ufe0f SHERPA",
        "jira": "\U0001f41b Jira",
        "slack": "\U0001f4ac Slack",
        "forum": "\U0001f310 Forum",
        "Percona Forums": "\U0001f310 Forum",
        "GitHub": "\U0001f4bb GitHub",
        "TAM Notes": "\U0001f4cb TAM",
        "SDM Notes": "\U0001f4cb SDM",
        "SE Feature Requests": "\U0001f4cb SE",
        "SE Prospect Requests": "\U0001f6a8 SE Blocker",
        "Salesforce": "\u2601\ufe0f SFDC",
        "ServiceNow": "\U0001f3ab SN",
        "Update.AI": "\U0001f3a5 Call",
        "Product Surveys": "\U0001f4dd Survey",
        "Zoom": "\U0001f3a5 Zoom",
        "6sense": "\U0001f4ca 6sense",
    }
    return badges.get(source, f"\U0001f4e5 {source}")


def _urgency_emoji(urgency: str) -> str:
    if urgency == "High":
        return "\U0001f534"   # 🔴
    if urgency == "Medium":
        return "\U0001f7e0"   # 🟠
    return "\U0001f7e2"       # 🟢


def format_new_signal(signal: DemandSignal, evidence: CustomerEvidence) -> dict:
    """Block Kit payload for a new demand signal with transparent scoring."""
    problem_line = f"\n:dart: _{signal.problem_statement}_" if signal.problem_statement else ""
    warning_line = f"\n:warning: {', '.join(signal.evidence_warnings)}" if signal.evidence_warnings else ""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "\U0001f195 New Demand Signal", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{signal.title}*{problem_line}\n"
                        f"{_source_badge(evidence.source)} | "
                        f"{_urgency_emoji(evidence.urgency)} {evidence.urgency} urgency\n"
                        f"Score: *{signal.demand_score:.1f}* "
                        f"(Biz: {signal.business_impact_score:.0f} | "
                        f"User: {signal.user_value_score:.0f}) | "
                        f"Confidence: *{signal.confidence_level}*"
                        f"{warning_line}"
                    ),
                },
            },
            {"type": "divider"},
        ]
    }


def format_evidence_added(signal: DemandSignal, evidence: CustomerEvidence) -> dict:
    """Block Kit payload for new evidence on an existing signal with score transparency."""
    warning_line = f"\n:warning: {', '.join(signal.evidence_warnings)}" if signal.evidence_warnings else ""
    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "\U0001f517 Evidence Merged", "emoji": True},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{signal.title}*\n"
                        f"{_source_badge(evidence.source)} | "
                        f"{_urgency_emoji(evidence.urgency)} {evidence.urgency}\n"
                        f"Evidence: *{len(signal.evidence)}* | "
                        f"Sources: *{signal.source_diversity}* types | "
                        f"Confidence: *{signal.confidence_level}*\n"
                        f"Score: *{signal.demand_score:.1f}* "
                        f"(Biz: {signal.business_impact_score:.0f} | "
                        f"User: {signal.user_value_score:.0f})"
                        f"{warning_line}"
                    ),
                },
            },
            {"type": "divider"},
        ]
    }


def notify(payload: dict) -> bool:
    """Post a Block Kit payload to the configured Slack webhook. Returns success."""
    if not SLACK_WEBHOOK_URL:
        log.debug("SHERPA_SLACK_WEBHOOK_URL not set, skipping notification")
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
