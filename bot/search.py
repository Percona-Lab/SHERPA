"""
SHERPA Enterprise Search — searches demand signals and customer evidence.

Phase 1: Direct Notion query.
Phase 2: IBEX integration for cross-source search.
"""

import logging

log = logging.getLogger("bot.search")


def search_signals(query, product_line=None, limit=10):
    """Search demand signals by query.

    First: search Notion SHERPA Demand Signals DB.
    If IBEX is available: also search Slack, Jira, etc. via IBEX MCP.

    Returns list of matching Notion pages.
    """
    from demand.notion_sync import _get_client, DEMAND_SIGNALS_DB
    client = _get_client()
    if not client:
        return []

    try:
        filter_obj = {
            "property": "Signal",
            "title": {"contains": query},
        }

        if product_line:
            filter_obj = {
                "and": [
                    filter_obj,
                    {"property": "Product Line", "select": {"equals": product_line}},
                ]
            }

        results = client.databases.query(
            database_id=DEMAND_SIGNALS_DB,
            filter=filter_obj,
            sorts=[{"property": "Demand Score", "direction": "descending"}],
            page_size=limit,
        )
        return results.get("results", [])
    except Exception as e:
        log.warning(f"Notion search failed: {e}")
        return []


def get_top_signals(product_line=None, limit=10):
    """Fetch top N signals sorted by Demand Score from Notion."""
    from demand.notion_sync import _get_client, DEMAND_SIGNALS_DB
    client = _get_client()
    if not client:
        return []

    try:
        kwargs = {
            "database_id": DEMAND_SIGNALS_DB,
            "sorts": [{"property": "Demand Score", "direction": "descending"}],
            "page_size": limit,
        }

        if product_line:
            kwargs["filter"] = {
                "property": "Product Line",
                "select": {"equals": product_line},
            }

        results = client.databases.query(**kwargs)
        return results.get("results", [])
    except Exception as e:
        log.warning(f"Top signals query failed: {e}")
        return []
