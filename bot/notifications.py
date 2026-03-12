"""
SHERPA Slack Bot — Channel notifications for #sherpa-signals.

Handles weekly digests, anomaly alerts, and proactive monitoring posts.
Webhook-based notifications remain in demand/slack_notify.py.
"""

import logging
import os

log = logging.getLogger("bot.notifications")


def format_weekly_digest(new_signals, merged_count, pending_reviews, top_movers):
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
            arrow = "\u2b06\ufe0f" if delta > 0 else "\u2b07\ufe0f"
            mover_lines.append(f"{arrow} *{title}* ({delta:+.1f} pts)")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Top Movers:*\n" + "\n".join(mover_lines)},
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
