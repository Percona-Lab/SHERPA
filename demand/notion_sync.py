"""
SHERPA Demand Engine — Read/write demand signals and evidence to Notion databases.

Requires `notion-client` package and NOTION_API_KEY env var.
If NOTION_API_KEY is not set, all operations are no-ops.
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

from .models import DemandSignal, CustomerEvidence

log = logging.getLogger("demand.notion_sync")

DEMAND_SIGNALS_DB = "67ca4fa6cb9b444390dd62008ccd819b"
CUSTOMER_EVIDENCE_DB = "9539dbfc3661420387c1e9705407bbd8"


def _get_client():
    """Lazy-init Notion client. Returns None if not configured."""
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        return None
    try:
        from notion_client import Client
        return Client(auth=api_key)
    except ImportError:
        log.warning("notion-client not installed — pip install notion-client")
        return None


# ─── Demand Signal Operations ───

def upsert_demand_signal(signal: DemandSignal) -> Optional[str]:
    """Create or update a demand signal page in Notion.

    Returns the Notion page ID, or None if sync is disabled.
    """
    notion = _get_client()
    if not notion:
        log.debug("Notion sync disabled (no API key or client)")
        return None

    existing = _find_signal_by_title(notion, signal.title)
    properties = _build_signal_properties(signal)

    if existing:
        page_id = existing["id"]
        notion.pages.update(page_id=page_id, properties=properties)
        log.info(f"Updated signal in Notion: '{signal.title}' ({page_id})")
        return page_id
    else:
        response = notion.pages.create(
            parent={"database_id": DEMAND_SIGNALS_DB},
            properties=properties,
        )
        page_id = response["id"]
        log.info(f"Created signal in Notion: '{signal.title}' ({page_id})")
        return page_id


def create_evidence(evidence: CustomerEvidence, signal_page_id: Optional[str] = None) -> Optional[str]:
    """Create an evidence page in the Customer Evidence Notion DB.

    Returns the Notion page ID, or None if sync is disabled.
    """
    notion = _get_client()
    if not notion:
        return None

    properties = _build_evidence_properties(evidence, signal_page_id)
    response = notion.pages.create(
        parent={"database_id": CUSTOMER_EVIDENCE_DB},
        properties=properties,
    )
    page_id = response["id"]
    log.info(f"Created evidence in Notion: '{evidence.summary}' ({page_id})")
    return page_id


def update_demand_score(signal_page_id: str, new_score: float):
    """Update just the Demand Score on an existing signal page."""
    notion = _get_client()
    if not notion:
        return
    notion.pages.update(
        page_id=signal_page_id,
        properties={
            "Demand Score": {"number": new_score},
            "Last Activity": {"date": {"start": datetime.utcnow().strftime("%Y-%m-%d")}},
        },
    )


def get_all_signals() -> List[dict]:
    """Fetch all demand signals from Notion (paginated)."""
    notion = _get_client()
    if not notion:
        return []

    all_results = []
    has_more = True
    start_cursor = None
    while has_more:
        kwargs = {"database_id": DEMAND_SIGNALS_DB}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
        response = notion.databases.query(**kwargs)
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    return all_results


# ─── Lookups ───

def _find_signal_by_title(notion, title: str) -> Optional[dict]:
    """Query Demand Signals DB for a page matching the given title."""
    try:
        results = notion.databases.query(
            database_id=DEMAND_SIGNALS_DB,
            filter={"property": "Signal", "title": {"equals": title}},
        )
        if results["results"]:
            return results["results"][0]
    except Exception as e:
        log.warning(f"Notion query failed: {e}")
    return None


# ─── Property Builders ───

def _build_signal_properties(signal: DemandSignal) -> dict:
    """Build Notion property dict from a DemandSignal."""
    props = {
        "Signal": {"title": [{"text": {"content": signal.title}}]},
        "Demand Score": {"number": signal.demand_score},
        "Category": {"select": {"name": signal.category}},
        "Last Activity": {"date": {"start": signal.last_activity or datetime.utcnow().strftime("%Y-%m-%d")}},
    }

    if signal.impact_score is not None:
        props["Impact Score"] = {"number": signal.impact_score}
    if signal.product_line:
        props["Product Line"] = {"select": {"name": signal.product_line}}
    if signal.urgency:
        props["Urgency"] = {"select": {"name": signal.urgency}}
    if signal.sources:
        props["Sources"] = {"multi_select": [{"name": s} for s in signal.sources]}
    if signal.total_mrr is not None:
        props["Total MRR Impact"] = {"number": signal.total_mrr}
    if signal.customer_count:
        props["Customer Count"] = {"number": signal.customer_count}
    if signal.community_mentions:
        props["Community Mentions"] = {"number": signal.community_mentions}
    if signal.strategic_alignment:
        props["Strategic Alignment"] = {"select": {"name": signal.strategic_alignment}}
    if signal.frequency:
        props["Frequency"] = {"select": {"name": signal.frequency}}
    if signal.first_reported:
        props["First Reported"] = {"date": {"start": signal.first_reported}}
    if signal.git_sha:
        props["Git SHA"] = {"rich_text": [{"text": {"content": signal.git_sha}}]}
    if signal.description:
        props["Description"] = {"rich_text": [{"text": {"content": signal.description[:2000]}}]}
    if signal.product_area:
        props["Product Area"] = {"rich_text": [{"text": {"content": signal.product_area}}]}
    if signal.jira_url:
        props["Jira Link"] = {"url": signal.jira_url}

    return props


def _build_evidence_properties(evidence: CustomerEvidence, signal_page_id: Optional[str] = None) -> dict:
    """Build Notion property dict from a CustomerEvidence."""
    # Map internal source names to Notion select options
    source_map = {
        "sherpa_vote": "SHERPA",
        "sherpa_comment": "SHERPA",
        "jira": "Jira",
        "slack": "Slack",
        "forum": "Percona Forums",
    }
    notion_source = source_map.get(evidence.source, evidence.source)

    props = {
        "Summary": {"title": [{"text": {"content": evidence.summary or evidence.title}}]},
        "Evidence Type": {"select": {"name": evidence.evidence_type}},
        "Source": {"select": {"name": notion_source}},
        "Date Captured": {"date": {"start": evidence.date_captured or datetime.utcnow().strftime("%Y-%m-%d")}},
    }

    if signal_page_id:
        props["Signal"] = {"relation": [{"id": signal_page_id}]}
    if evidence.confidence_label:
        props["Confidence"] = {"select": {"name": evidence.confidence_label}}
    if evidence.ingested_by:
        props["Ingested By"] = {"select": {"name": evidence.ingested_by}}
    if evidence.mrr is not None:
        props["MRR"] = {"number": evidence.mrr}
    if evidence.account_name:
        props["Account Name"] = {"rich_text": [{"text": {"content": evidence.account_name}}]}
    if evidence.contact:
        props["Contact"] = {"rich_text": [{"text": {"content": evidence.contact}}]}
    if evidence.verbatim:
        props["Verbatim"] = {"rich_text": [{"text": {"content": evidence.verbatim[:2000]}}]}
    if evidence.source_url:
        props["Source URL"] = {"url": evidence.source_url}
    if evidence.sentiment:
        props["Sentiment"] = {"select": {"name": evidence.sentiment}}
    if evidence.product_line:
        props["Product Line"] = {"select": {"name": evidence.product_line}}

    return props
