"""
SHERPA Demand Engine — Clari Copilot Connector.

Ingests AI call summaries from Clari Copilot as customer evidence.
Each call can generate multiple evidence entries (one per product area discussed).

Reads the call index JSON built by the Clari MCP server (same VM) and calls
the Clari REST API directly for summaries using shared credentials.

Usage:
    from demand.clari_connector import sync_clari_calls
    results = sync_clari_calls(days=30, limit=100)

    # Dry run to preview what would be ingested:
    results = sync_clari_calls(days=7, dry_run=True)
"""

import hashlib
import logging
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

from .models import CustomerEvidence
from .ingestion import ingest_evidence

log = logging.getLogger("demand.clari_connector")

# Load Clari API credentials from same .env as the MCP server
_relay_env = Path.home() / "relay-bridge" / ".env"
if _relay_env.exists():
    load_dotenv(_relay_env)

CLARI_API_KEY = os.environ.get("CLARI_API_KEY", "")
CLARI_API_PASSWORD = os.environ.get("CLARI_API_PASSWORD", "")
CLARI_BASE_URL = os.environ.get("CLARI_BASE_URL", "https://rest-api.copilot.clari.com")

# Call index built by the Clari MCP server
CALL_INDEX_PATH = Path.home() / "relay-bridge" / "call_index.json"

# Track which calls we've already ingested
_DATA_DIR = Path(os.environ.get("SHERPA_DATA_DIR", str(Path(__file__).resolve().parent.parent)))
INGESTED_CALLS_FILE = _DATA_DIR / "clari_ingested.json"

# Service-type areas to skip (not product lines)
SERVICE_AREAS = {"ExpertOps", "Support", "Consulting"}


def _load_ingested() -> dict:
    """Load the set of already-ingested call IDs with timestamps."""
    if INGESTED_CALLS_FILE.exists():
        try:
            return json.loads(INGESTED_CALLS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_ingested(data: dict) -> None:
    """Persist the ingested call tracking data."""
    INGESTED_CALLS_FILE.write_text(json.dumps(data, indent=2))


def _evidence_id(call_id: str, product_area: str) -> str:
    """Generate a deterministic evidence ID for a call + product area combo."""
    raw = f"clari-{call_id}-{product_area}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _map_urgency(market_signals: List[str]) -> str:
    """Map Clari market signals to SHERPA urgency levels."""
    if "Churn Risk" in market_signals:
        return "Churn Risk"
    high_signals = {"Migration", "Competitive Eval", "Performance Issue"}
    if high_signals & set(market_signals):
        return "High"
    medium_signals = {"Upgrade", "Cloud Migration", "Compliance/Security", "HA/DR"}
    if medium_signals & set(market_signals):
        return "Medium"
    return "Low"


def _map_sentiment(market_signals: List[str]) -> str:
    """Derive sentiment from market signals."""
    if "Churn Risk" in market_signals:
        return "Churn Signal"
    if "Competitive Eval" in market_signals:
        return "Negative"
    if "Expansion" in market_signals or "New Deployment" in market_signals:
        return "Positive"
    return "Neutral"


def _map_product_line(product_area: str) -> str:
    """Map Clari product areas to SHERPA product line names."""
    mapping = {
        "MySQL": "MySQL",
        "PostgreSQL": "PostgreSQL",
        "MongoDB": "MongoDB",
        "PMM": "PMM",
        "Operators": "Operators",
        "Everest": "Open Everest",
        "Valkey": "Valkey",
        "Percona Toolkit": "Percona Toolkit",
        "Pro Builds": "Pro Builds",
    }
    return mapping.get(product_area, product_area)


def _load_call_index() -> List[dict]:
    """Load the call index JSON built by the Clari MCP server."""
    if not CALL_INDEX_PATH.exists():
        raise FileNotFoundError(f"Call index not found at {CALL_INDEX_PATH}")
    data = json.loads(CALL_INDEX_PATH.read_text())
    # Index can be a list or a dict with a "calls" key
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("calls", list(data.values()))
    return []


def _fetch_summary(call_id: str) -> dict:
    """Fetch AI summary from Clari REST API."""
    if not CLARI_API_KEY or not CLARI_API_PASSWORD:
        raise ValueError("CLARI_API_KEY and CLARI_API_PASSWORD must be set")

    headers = {
        "X-Api-Key": CLARI_API_KEY,
        "X-Api-Password": CLARI_API_PASSWORD,
        "Accept": "application/json",
    }
    resp = requests.get(
        f"{CLARI_BASE_URL}/v1/calls/{call_id}/smart-summary",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 404:
        return {}
    resp.raise_for_status()
    return resp.json()


def call_to_evidence(
    call_meta: dict,
    summary_data: dict,
    product_area: str,
) -> CustomerEvidence:
    """Convert a Clari call + summary into CustomerEvidence for a specific product area."""
    call_id = call_meta["call_id"]
    title = call_meta.get("title", "Untitled Call")
    account = call_meta.get("account_name", "")
    signals = call_meta.get("market_signals", [])
    external = call_meta.get("external_participants", [])
    users = call_meta.get("users", [])
    call_date = call_meta.get("date", "")

    # Extract summary text
    summary_obj = summary_data.get("summary", summary_data)
    full_summary = summary_obj.get("full_summary", "") if isinstance(summary_obj, dict) else str(summary_obj)
    key_takeaways = summary_obj.get("key_takeaways", "") if isinstance(summary_obj, dict) else ""

    # Use key takeaways as description if available
    description = key_takeaways if key_takeaways else full_summary
    if not description:
        description = f"Call about {_map_product_line(product_area)} with {account or 'unknown customer'}"

    # Build contact info
    contact = ", ".join(external[:3]) if external else ""
    percona_attendees = ", ".join(
        u.split("@")[0].replace(".", " ").title() for u in users[:3]
    )

    return CustomerEvidence(
        id=_evidence_id(call_id, product_area),
        source="Clari Copilot",
        source_type="External",
        title=f"{title} - {_map_product_line(product_area)}",
        description=description[:3000],
        customer_name=account if account else (external[0] if external else "Unknown"),
        customer_email=external[0] if external and "@" in str(external[0]) else "",
        urgency=_map_urgency(signals),
        confidence=0.75,
        score_weight=2.0,
        raw_data={
            "call_id": call_id,
            "call_title": title,
            "call_date": call_date,
            "account_name": account,
            "deal_name": call_meta.get("deal_name", ""),
            "market_signals": signals,
            "product_areas": call_meta.get("product_areas", []),
            "percona_attendees": percona_attendees,
            "external_participants": external,
            "duration_sec": call_meta.get("duration_sec", 0),
        },
        summary=f"Call: {title}" + (f" ({account})" if account else ""),
        evidence_type="Customer" if account else "Internal",
        confidence_label="High" if account else "Medium",
        ingested_by="Agent - Scheduled",
        account_name=account,
        contact=contact,
        verbatim=(full_summary or "")[:2000],
        source_url=None,
        sentiment=_map_sentiment(signals),
        product_line=_map_product_line(product_area),
        date_captured=call_date,
    )


def sync_clari_calls(
    days: int = 30,
    limit: int = 200,
    product_areas: Optional[List[str]] = None,
    market_signals: Optional[List[str]] = None,
    dry_run: bool = False,
) -> dict:
    """Sync Clari Copilot calls into SHERPA demand engine.

    Args:
        days: Look back this many days for calls.
        limit: Max calls to process.
        product_areas: Filter by product areas (None = all product areas).
        market_signals: Filter by market signals (None = all).
        dry_run: If True, don't actually ingest - just return what would be ingested.

    Returns:
        Dict with counts: total_calls, new_calls, evidence_created, skipped, errors.
    """
    ingested = _load_ingested()
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    results = {
        "total_calls": 0,
        "new_calls": 0,
        "evidence_created": 0,
        "skipped": 0,
        "errors": 0,
        "dry_run": dry_run,
        "details": [],
    }

    # Load call index
    try:
        all_calls = _load_call_index()
    except Exception as e:
        log.error(f"Failed to load call index: {e}")
        results["errors"] += 1
        return results

    # Filter by date
    calls = [c for c in all_calls if c.get("date", "") >= cutoff_date]

    # Filter by product areas if specified
    if product_areas:
        pa_set = set(product_areas)
        calls = [c for c in calls if pa_set & set(c.get("product_areas", []))]

    # Filter by market signals if specified
    if market_signals:
        ms_set = set(market_signals)
        calls = [c for c in calls if ms_set & set(c.get("market_signals", []))]

    # Sort by date descending and apply limit
    calls.sort(key=lambda c: c.get("date", ""), reverse=True)
    calls = calls[:limit]
    results["total_calls"] = len(calls)

    for call in calls:
        call_id = call.get("call_id", "")
        if not call_id:
            continue

        # Skip already-ingested calls
        if call_id in ingested:
            results["skipped"] += 1
            continue

        results["new_calls"] += 1

        # Filter to product-relevant areas (skip service types)
        product_only = [
            pa for pa in call.get("product_areas", [])
            if pa not in SERVICE_AREAS
        ]
        if not product_only:
            results["skipped"] += 1
            continue

        # Fetch summary from Clari API
        summary = {}
        if not dry_run:
            try:
                summary = _fetch_summary(call_id)
            except Exception as e:
                log.warning(f"Failed to get summary for call {call_id}: {e}")
                results["errors"] += 1
                continue

        # Create one evidence entry per product area
        for product_area in product_only:
            try:
                evidence = call_to_evidence(call, summary, product_area)

                if dry_run:
                    results["details"].append({
                        "call_id": call_id,
                        "title": call.get("title"),
                        "date": call.get("date"),
                        "account": call.get("account_name"),
                        "product_line": _map_product_line(product_area),
                        "urgency": evidence.urgency,
                        "sentiment": evidence.sentiment,
                        "market_signals": call.get("market_signals", []),
                    })
                else:
                    ingest_evidence(evidence)

                results["evidence_created"] += 1
            except Exception as e:
                log.warning(f"Failed to ingest evidence from call {call_id} ({product_area}): {e}")
                results["errors"] += 1

        # Mark call as ingested
        if not dry_run:
            ingested[call_id] = {
                "title": call.get("title", ""),
                "date": call.get("date", ""),
                "account": call.get("account_name", ""),
                "ingested_at": datetime.utcnow().isoformat() + "Z",
                "product_areas": product_only,
            }

        # Rate limit Clari API (10 req/sec limit)
        if not dry_run:
            time.sleep(0.2)

    # Save state
    if not dry_run:
        _save_ingested(ingested)

    log.info(
        f"Clari sync complete: {results['total_calls']} calls, "
        f"{results['new_calls']} new, {results['evidence_created']} evidence created, "
        f"{results['skipped']} skipped, {results['errors']} errors"
    )
    return results
