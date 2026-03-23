"""
SHERPA Slack Bot — Channel notifications for #sherpa-signals.

Discovery-informed: notifications surface dual scores, confidence levels,
and anti-SCORE warnings so PMs never see an opaque number without context.
"""

import logging
import os

log = logging.getLogger("bot.notifications")


def _score_breakdown(signal) -> str:
    """Format transparent score breakdown for a signal."""
    parts = [
        f"*Demand Score:* {signal.demand_score:.1f}",
        f"  Biz Impact: {signal.business_impact_score:.0f}  |  User Value: {signal.user_value_score:.0f}",
        f"  Confidence: {signal.confidence_level}  |  Sources: {signal.source_diversity} types",
    ]
    return "\n".join(parts)


def _warning_badges(warnings) -> str:
    """Format anti-SCORE warnings as visible badges."""
    if not warnings:
        return ""
    emoji_map = {
        "Sparse Evidence": ":warning:",
        "Single Source": ":one:",
        "Stale Data": ":hourglass:",
        "No Customer Data": ":bust_in_silhouette:",
        "No Community Data": ":globe_with_meridians:",
        "Contradictory Signals": ":left_right_arrow:",
    }
    badges = [f"{emoji_map.get(w, ':grey_question:')} {w}" for w in warnings]
    return "\n".join(badges)


def format_weekly_digest(new_signals, merged_count, pending_reviews, top_movers,
                         weak_signals=None):
    """Weekly Monday digest for #sherpa-signals."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "\U0001f4ca SHERPA Weekly Digest", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"\u2022 *{new_signals}* new demand signals this week\n"
                    f"\u2022 *{merged_count}* evidence items merged\n"
                    f"\u2022 *{pending_reviews}* signals pending review"
                ),
            },
        },
    ]

    if top_movers:
        mover_lines = []
        for m in top_movers[:5]:
            title = m.get("title", "?")
            delta = m.get("delta", 0)
            confidence = m.get("confidence_level", "?")
            arrow = "\u2b06\ufe0f" if delta > 0 else "\u2b07\ufe0f"
            mover_lines.append(f"{arrow} *{title}* ({delta:+.1f} pts, {confidence})")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Top Movers:*\n" + "\n".join(mover_lines)},
        })

    # Anti-SCORE: surface signals with weak evidence that are ranking high
    if weak_signals:
        weak_lines = []
        for s in weak_signals[:3]:
            title = s.get("title", "?")
            warnings = ", ".join(s.get("warnings", []))
            weak_lines.append(f":warning: *{title}* — {warnings}")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:mag: Needs Attention (weak evidence):*\n" + "\n".join(weak_lines),
            },
        })

    blocks.append({"type": "divider"})
    return {"blocks": blocks}


def format_anomaly_alert(alert_type, details):
    """Proactive alert when something crosses a significance threshold.

    alert_type: "demand_spike" | "cluster_detected" | "churn_risk" | "trending"
    """
    emoji_map = {
        "demand_spike": "\U0001f4c8",    # 📈
        "cluster_detected": "\U0001f9e9", # 🧩
        "churn_risk": "\U0001f6a8",       # 🚨
        "trending": "\U0001f525",         # 🔥
    }
    emoji = emoji_map.get(alert_type, "\u26a0\ufe0f")
    title = alert_type.replace("_", " ").title()

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": details},
            },
            {"type": "divider"},
        ]
    }


def format_signal_card(signal) -> dict:
    """Format a single signal as a rich Slack message with full transparency.

    Shows dual scores, confidence, source diversity, and any warnings.
    This is the core anti-SCORE mechanism: PMs always see WHY a signal
    ranks where it does, not just a number.
    """
    score_text = _score_breakdown(signal)
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{signal.title}*\n{score_text}",
            },
        },
    ]

    if signal.problem_statement:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f":dart: *Problem:* {signal.problem_statement}"},
            ],
        })

    warnings_text = _warning_badges(signal.evidence_warnings)
    if warnings_text:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": warnings_text},
            ],
        })

    evidence_summary = (
        f"{signal.customer_count} customers | "
        f"{signal.community_mentions} community | "
        f"{len(signal.evidence)} total evidence"
    )
    if signal.total_mrr:
        evidence_summary += f" | ${signal.total_mrr:,.0f} MRR"
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": evidence_summary}],
    })

    blocks.append({"type": "divider"})
    return {"blocks": blocks}


def send_to_channel(blocks, channel_id=None):
    """Post blocks to #sherpa-signals (or specified channel)."""
    channel = channel_id or os.getenv("SHERPA_SIGNALS_CHANNEL")
    if not channel:
        log.debug("No channel configured for notifications")
        return

    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        log.debug("No SLACK_BOT_TOKEN, skipping channel post")
        return

    try:
        from slack_sdk import WebClient
        client = WebClient(token=token)
        client.chat_postMessage(channel=channel, blocks=blocks)
    except Exception as e:
        log.warning(f"Channel notification failed: {e}")
