"""
SHERPA Demand Engine — Read/write demand signals and evidence to Notion databases.

Requires `notion-client` package and NOTION_API_KEY env var.
If NOTION_API_KEY is not set, all operations are no-ops.

Read path: SQLite cache with 5-min TTL for snappy UI responses.
"""

import json
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests as _requests

from .models import DemandSignal, CustomerEvidence

log = logging.getLogger("demand.notion_sync")

DEMAND_SIGNALS_DB = "67ca4fa6cb9b444390dd62008ccd819b"
CUSTOMER_EVIDENCE_DB = "9539dbfc3661420387c1e9705407bbd8"

CACHE_TTL = 300  # 5 minutes
_CACHE_DB_PATH = Path(__file__).parent.parent / "portal.db"


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


# ─── SQLite Cache ───

def _ensure_cache_table(db: sqlite3.Connection):
    db.execute("""
        CREATE TABLE IF NOT EXISTS notion_cache (
            cache_key TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at REAL NOT NULL
        )
    """)
    db.commit()


def _cache_get(key: str) -> Optional[list]:
    """Return cached data if fresh, else None."""
    try:
        db = sqlite3.connect(str(_CACHE_DB_PATH))
        _ensure_cache_table(db)
        row = db.execute(
            "SELECT data, fetched_at FROM notion_cache WHERE cache_key = ?", (key,)
        ).fetchone()
        db.close()
        if row and (time.time() - row[1]) < CACHE_TTL:
            return json.loads(row[0])
    except Exception as e:
        log.debug(f"Cache read error: {e}")
    return None


def _cache_set(key: str, data: list):
    """Store data in cache."""
    try:
        db = sqlite3.connect(str(_CACHE_DB_PATH))
        _ensure_cache_table(db)
        db.execute(
            "INSERT OR REPLACE INTO notion_cache (cache_key, data, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(data, default=str), time.time()),
        )
        db.commit()
        db.close()
    except Exception as e:
        log.debug(f"Cache write error: {e}")


# ─── Notion Property Extractors ───

def _extract_text(prop: dict) -> str:
    """Extract plain text from a Notion rich_text or title property."""
    prop_type = prop.get("type", "")
    items = prop.get(prop_type, [])
    if isinstance(items, list):
        return "".join(t.get("plain_text", "") for t in items)
    return ""


def _extract_select(prop: dict) -> str:
    sel = prop.get("select")
    return sel.get("name", "") if sel else ""


def _extract_multi_select(prop: dict) -> List[str]:
    return [o.get("name", "") for o in prop.get("multi_select", [])]


def _extract_number(prop: dict) -> Optional[float]:
    return prop.get("number")


def _extract_date(prop: dict) -> str:
    d = prop.get("date")
    return d.get("start", "") if d else ""


def _extract_url(prop: dict) -> Optional[str]:
    return prop.get("url")


def _extract_relation_ids(prop: dict) -> List[str]:
    return [r.get("id", "") for r in prop.get("relation", [])]


def _parse_signal_page(page: dict) -> dict:
    """Parse a Notion page from the Demand Signals DB into a flat dict."""
    props = page.get("properties", {})
    page_id = page["id"]

    # Title is "Signal"
    title = _extract_text(props.get("Signal", {}))
    description = _extract_text(props.get("Description", {}))
    category = _extract_select(props.get("Category", {}))
    product_line = _extract_select(props.get("Product Line", {}))
    urgency = _extract_select(props.get("Urgency", {}))
    strategic_alignment = _extract_select(props.get("Strategic Alignment", {}))
    confidence_level = _extract_select(props.get("Confidence Level", {}))

    demand_score = _extract_number(props.get("Demand Score", {})) or 0
    impact_score = _extract_number(props.get("Impact Score", {}))
    business_impact = _extract_number(props.get("Business Impact Score", {})) or 0
    user_value = _extract_number(props.get("User Value Score", {})) or 0
    total_mrr = _extract_number(props.get("Total MRR Impact", {}))
    customer_count = _extract_number(props.get("Customer Count", {})) or 0
    community_mentions = _extract_number(props.get("Community Mentions", {})) or 0
    source_diversity = _extract_number(props.get("Source Diversity", {})) or 0

    sources = _extract_multi_select(props.get("Sources", {}))
    evidence_warnings = _extract_multi_select(props.get("Evidence Warnings", {}))
    customers = _extract_multi_select(props.get("Customers", {}))

    problem_statement = _extract_text(props.get("Problem Statement", {}))
    product_area = _extract_text(props.get("Product Area", {}))
    jira_url = _extract_url(props.get("Jira Link", {}))

    last_activity = _extract_date(props.get("Last Activity", {}))
    first_reported = _extract_date(props.get("First Reported", {}))

    # Evidence relation IDs (for linking)
    evidence_ids = _extract_relation_ids(props.get("Evidence", {}))

    return {
        "id": page_id,
        "title": title,
        "description": description,
        "category": category,
        "product_line": product_line,
        "urgency": urgency,
        "strategic_alignment": strategic_alignment,
        "confidence_level": confidence_level,
        "demand_score": demand_score,
        "impact_score": impact_score,
        "business_impact_score": business_impact,
        "user_value_score": user_value,
        "total_mrr": total_mrr,
        "customer_count": int(customer_count),
        "community_mentions": int(community_mentions),
        "source_diversity": int(source_diversity),
        "sources": sources,
        "evidence_warnings": evidence_warnings,
        "customers": customers,
        "problem_statement": problem_statement,
        "product_area": product_area,
        "jira_url": jira_url,
        "last_activity": last_activity,
        "first_reported": first_reported,
        "evidence_ids": evidence_ids,
        "notion_url": f"https://www.notion.so/{page_id.replace('-', '')}",
    }


def _parse_evidence_page(page: dict) -> dict:
    """Parse a Notion page from the Customer Evidence DB into a flat dict."""
    props = page.get("properties", {})
    page_id = page["id"]

    summary = _extract_text(props.get("Summary", {}))
    evidence_type = _extract_select(props.get("Evidence Type", {}))
    source = _extract_select(props.get("Source", {}))
    confidence = _extract_select(props.get("Confidence", {}))
    sentiment = _extract_select(props.get("Sentiment", {}))
    product_line = _extract_select(props.get("Product Line", {}))
    ingested_by = _extract_select(props.get("Ingested By", {}))

    mrr = _extract_number(props.get("MRR", {}))
    account_name = _extract_text(props.get("Account Name", {}))
    contact = _extract_text(props.get("Contact", {}))
    verbatim = _extract_text(props.get("Verbatim", {}))
    source_url = _extract_url(props.get("Source URL", {}))
    date_captured = _extract_date(props.get("Date Captured", {}))

    signal_ids = _extract_relation_ids(props.get("Signal", {}))

    return {
        "id": page_id,
        "summary": summary,
        "evidence_type": evidence_type,
        "source": source,
        "confidence": confidence,
        "sentiment": sentiment,
        "product_line": product_line,
        "ingested_by": ingested_by,
        "mrr": mrr,
        "account_name": account_name,
        "contact": contact,
        "verbatim": verbatim,
        "source_url": source_url,
        "date_captured": date_captured,
        "signal_ids": signal_ids,
        "notion_url": f"https://www.notion.so/{page_id.replace('-', '')}",
    }


# ─── Notion REST Query (bypasses SDK version issues) ───

def _query_database(database_id: str) -> List[dict]:
    """Query a Notion database via REST API. Returns all pages (paginated)."""
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        return []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    all_results = []
    payload = {}
    has_more = True
    while has_more:
        resp = _requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers, json=payload, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        if has_more:
            payload["start_cursor"] = data["next_cursor"]
    return all_results


# ─── Cached Read Operations ───

def get_demand_signals_cached() -> List[dict]:
    """Fetch all demand signals with SQLite cache (5-min TTL)."""
    cached = _cache_get("demand_signals")
    if cached is not None:
        return cached

    try:
        pages = _query_database(DEMAND_SIGNALS_DB)
    except Exception as e:
        log.error(f"Failed to fetch demand signals: {e}")
        return []

    parsed = [_parse_signal_page(p) for p in pages]
    _cache_set("demand_signals", parsed)
    return parsed


def get_customer_evidence_cached() -> List[dict]:
    """Fetch all customer evidence with SQLite cache (5-min TTL)."""
    cached = _cache_get("customer_evidence")
    if cached is not None:
        return cached

    try:
        pages = _query_database(CUSTOMER_EVIDENCE_DB)
    except Exception as e:
        log.error(f"Failed to fetch customer evidence: {e}")
        return []

    parsed = [_parse_evidence_page(p) for p in pages]
    _cache_set("customer_evidence", parsed)
    return parsed


def get_signal_with_evidence(signal_id: str) -> Optional[dict]:
    """Get a single signal with all its linked evidence."""
    signals = get_demand_signals_cached()
    signal = next((s for s in signals if s["id"] == signal_id), None)
    if not signal:
        return None

    all_evidence = get_customer_evidence_cached()
    # Match evidence to signal via relation
    linked = [e for e in all_evidence if signal_id in e.get("signal_ids", [])]
    signal["evidence"] = linked
    return signal


def invalidate_cache():
    """Force-clear the Notion cache."""
    try:
        db = sqlite3.connect(str(_CACHE_DB_PATH))
        _ensure_cache_table(db)
        db.execute("DELETE FROM notion_cache")
        db.commit()
        db.close()
    except Exception as e:
        log.debug(f"Cache invalidation error: {e}")


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
    try:
        return _query_database(DEMAND_SIGNALS_DB)
    except Exception as e:
        log.error(f"Failed to fetch signals: {e}")
        return []


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

    # Discovery-informed fields: dual scores, confidence, warnings
    props["Business Impact Score"] = {"number": signal.business_impact_score}
    props["User Value Score"] = {"number": signal.user_value_score}
    props["Source Diversity"] = {"number": signal.source_diversity}
    if signal.confidence_level:
        props["Confidence Level"] = {"select": {"name": signal.confidence_level}}
    if signal.evidence_warnings:
        props["Evidence Warnings"] = {"multi_select": [{"name": w} for w in signal.evidence_warnings]}
    if signal.problem_statement:
        props["Problem Statement"] = {"rich_text": [{"text": {"content": signal.problem_statement[:2000]}}]}

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
