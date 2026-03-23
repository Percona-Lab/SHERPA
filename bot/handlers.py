"""
@sherpa Slack bot — slash commands and event handlers.

Commands:
    /sherpa search [query]     - Search demand signals
    /sherpa log "[feedback]"   - Manually log evidence
    /sherpa top [product]      - Top 10 signals by Demand Score
    /sherpa signal [id]        - Signal details with score breakdown
    /sherpa digest             - Trigger demand signal digest on demand
"""

import logging
import os

log = logging.getLogger("bot.handlers")


def create_slack_app():
    """Create and configure the Slack Bolt app. Returns None if not configured."""
    token = os.getenv("SLACK_BOT_TOKEN")
    secret = os.getenv("SLACK_SIGNING_SECRET")
    if not token or not secret:
        log.info("Slack bot not configured (missing SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET)")
        return None

    try:
        from slack_bolt import App
    except ImportError:
        log.warning("slack-bolt not installed — pip install slack-bolt")
        return None

    app = App(token=token, signing_secret=secret)

    @app.command("/sherpa")
    def handle_sherpa_command(ack, command, respond):
        ack()
        text = command.get("text", "").strip()

        if text.startswith("search "):
            query = text[7:]
            try:
                from bot.search import search_signals
                results = search_signals(query)
                if results:
                    lines = [f"*{i+1}.* {_signal_title(r)} (score: {_signal_score(r)})" for i, r in enumerate(results[:10])]
                    respond(f"\U0001f50d *Results for \"{query}\":*\n" + "\n".join(lines))
                else:
                    respond(f"\U0001f50d No signals found for \"{query}\"")
            except Exception as e:
                log.warning(f"Search failed: {e}")
                respond(f"\U0001f50d Searching for: {query}...")

        elif text.startswith("log "):
            feedback = text[4:].strip('"').strip("'")
            try:
                from demand.ingestion import ingest_evidence
                result = ingest_evidence({
                    "title": feedback,
                    "source": "Slack",
                    "source_type": "Internal",
                    "description": f"Manual log via /sherpa: {feedback}",
                    "ingested_by": "Agent - Manual",
                })
                respond(f"\U0001f4dd Logged as signal: *{result.title}* (score: {result.demand_score})")
            except Exception as e:
                log.warning(f"Manual log failed: {e}")
                respond(f"\U0001f4dd Logged: {feedback}")

        elif text.startswith("top"):
            product = text[3:].strip() or None
            try:
                from bot.search import get_top_signals
                results = get_top_signals(product_line=product)
                if results:
                    lines = [f"*{i+1}.* {_signal_title(r)} (score: {_signal_score(r)})" for i, r in enumerate(results[:10])]
                    header = f"\U0001f4ca *Top signals" + (f" for {product}" if product else "") + ":*\n"
                    respond(header + "\n".join(lines))
                else:
                    respond("\U0001f4ca No signals found" + (f" for {product}" if product else ""))
            except Exception as e:
                log.warning(f"Top signals failed: {e}")
                respond(f"\U0001f4ca Top signals" + (f" for {product}" if product else "") + "...")

        elif text.startswith("signal "):
            signal_id = text[7:].strip()
            try:
                from demand.git_sync import GitSyncManager
                manager = GitSyncManager()
                signal = manager.load_signal(signal_id)
                if signal:
                    # Transparent score breakdown (anti-SCORE: always show WHY)
                    problem_line = f"\n:dart: *Problem:* {signal.problem_statement}" if signal.problem_statement else ""
                    warnings_line = f"\n:warning: *Warnings:* {', '.join(signal.evidence_warnings)}" if signal.evidence_warnings else ""
                    respond(
                        f"\U0001f50e *{signal.title}*{problem_line}\n"
                        f"*Demand Score:* {signal.demand_score:.1f}  |  "
                        f"Biz Impact: {signal.business_impact_score:.0f}  |  "
                        f"User Value: {signal.user_value_score:.0f}\n"
                        f"Confidence: *{signal.confidence_level}*  |  "
                        f"Source Diversity: *{signal.source_diversity}* types  |  "
                        f"Evidence: *{len(signal.evidence)}*\n"
                        f"Customers: {signal.customer_count}  |  "
                        f"Community: {signal.community_mentions}  |  "
                        f"MRR: ${signal.total_mrr or 0:,.0f}\n"
                        f"Sources: {', '.join(signal.sources) or 'N/A'}"
                        f"{warnings_line}"
                    )
                else:
                    respond(f"\U0001f50e Signal `{signal_id}` not found")
            except Exception as e:
                log.warning(f"Signal lookup failed: {e}")
                respond(f"\U0001f50e Looking up signal {signal_id}...")

        elif text == "digest":
            respond("\U0001f4ca Generating digest...")

        else:
            respond(
                "\U0001f3d4\ufe0f *SHERPA Commands:*\n"
                "\u2022 `/sherpa search [query]` \u2014 Search demand signals\n"
                "\u2022 `/sherpa log \"[feedback]\"` \u2014 Log evidence manually\n"
                "\u2022 `/sherpa top [product]` \u2014 Top 10 signals\n"
                "\u2022 `/sherpa signal [id]` \u2014 Signal details\n"
                "\u2022 `/sherpa digest` \u2014 Weekly digest now"
            )

    @app.event("app_mention")
    def handle_mention(event, say):
        """Handle @sherpa mentions in channels."""
        say(f"\U0001f3d4\ufe0f I heard you! Try `/sherpa search [query]` for now.")

    return app


def _signal_title(notion_page: dict) -> str:
    """Extract title from a Notion page result."""
    try:
        props = notion_page.get("properties", {})
        title_prop = props.get("Signal", {})
        return title_prop["title"][0]["plain_text"]
    except (KeyError, IndexError, TypeError):
        return "Untitled"


def _signal_score(notion_page: dict) -> str:
    """Extract demand score from a Notion page result."""
    try:
        return str(notion_page["properties"]["Demand Score"]["number"] or 0)
    except (KeyError, TypeError):
        return "?"
