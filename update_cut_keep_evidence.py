"""Update cut_keep_features with evidence from Jira, Clari Copilot, and PostHog sweeps."""

import json
import math
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "portal.db"

EVIDENCE = {
    "LOCK TABLES FOR BACKUP": {
        "jira_ticket_count": 3,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 2234,
    },
    "Slow query log rotation and expiration": {
        "jira_ticket_count": 4,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 1263,
    },
    "PXB estimate memory": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 85,
    },
    "Utility user": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 694,
    },
    "JS stored procedure": {
        "jira_ticket_count": 13,
        "clari_mention_count": 1,
        "docs_pageviews_24m": 202,
    },
    "Adaptive network buffers": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 1159,
    },
    "Extended SELECT INTO OUTFILE/DUMPFILE": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 424,
    },
    "LDAP Plugin": {
        "jira_ticket_count": 3,
        "clari_mention_count": 1,
        "docs_pageviews_24m": 2027,
    },
    "MeCAB Plugin": {
        "jira_ticket_count": 3,
        "clari_mention_count": 0,
        "docs_pageviews_24m": None,
    },
    "Audit Log Plugin (Old)": {
        "jira_ticket_count": 86,
        "clari_mention_count": 3,
        "docs_pageviews_24m": 12913,
    },
    "Keyring plugins/components": {
        "jira_ticket_count": 33,
        "clari_mention_count": 1,
        "docs_pageviews_24m": 1808,
    },
    "GCache and WS Encryption": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": None,
    },
    "MyRocks": {
        "jira_ticket_count": 63,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 2129,
    },
    "NBO (non-blocking DDLs)": {
        "jira_ticket_count": 2,
        "clari_mention_count": 0,
        "docs_pageviews_24m": None,
    },
    "PXC Scheduler Handler": {
        "jira_ticket_count": 1,
        "clari_mention_count": 0,
        "docs_pageviews_24m": None,
    },
    "ProxySQL Admin Scripts": {
        "jira_ticket_count": 0,
        "clari_mention_count": 0,
        "docs_pageviews_24m": 3357,
    },
    "Reduced Lock": {
        "jira_ticket_count": 0,
        "clari_mention_count": 1,
        "docs_pageviews_24m": None,
    },
}

EVIDENCE_SUMMARIES = {
    "LOCK TABLES FOR BACKUP": "Strong docs signal (2,234 views, ~93/mo). 3 Jira tickets (crash bug, code refresh). No Clari mentions. Backup-adjacent feature with sustained docs interest.",
    "Slow query log rotation and expiration": "Moderate docs traffic (1,263 views, ~53/mo). 4 Jira tickets including a crash bug (PS-10128) and doc improvements. Actively maintained.",
    "PXB estimate memory": "Minimal docs traffic (85 views, ~4/mo) — only documented as anchor on option reference page, not standalone. Zero Jira or Clari activity. Lowest evidence of all v0 features.",
    "Utility user": "Moderate docs traffic (694 views, ~29/mo). Zero Jira or Clari activity despite docs interest. Possible adoption barrier — customers reading docs but not filing tickets.",
    "JS stored procedure": "Active development (13 Jira tickets — Epic for GA, crash bugs, telemetry, conference talks). 1 Clari mention (Coupa requested this). Newer feature with growing docs traffic (202 views since Jan 2025, trending up).",
    "Adaptive network buffers": "Good docs traffic (1,159 views, ~48/mo) and telemetry shows active use. Zero Jira activity — stable feature. Docs interest + telemetry = keep signal.",
    "Extended SELECT INTO OUTFILE/DUMPFILE": "Low docs traffic (424 views, ~18/mo), telemetry shows use, but zero Jira or Clari activity. Quiet but active in production.",
    "LDAP Plugin": "Strong docs signal (2,027 views). 3 Jira tickets (bug fix, docs review, Okta auth). 1 Clari mention (Spinnaker enterprise requirements). Part of broader auth ecosystem (OIDC).",
    "MeCAB Plugin": "3 Jira tickets (phrase search PR, adjacency bug, boolean mode optimization). No docs page found, no Clari mentions. Niche Japanese full-text tokenizer with active bug fixes.",
    "Audit Log Plugin (Old)": "Strongest signal across all sources. 12,913 docs pageviews (~538/mo). 86 Jira tickets (memory leaks, crashes, filter improvements, JSONL format). 3 Clari calls (Coupa, Arista, Choice Home). Clear keep — despite being 'old', heavily used.",
    "Keyring plugins/components": "Strong cross-source signal. 1,808 docs views. 33 Jira tickets (KMIP crashes, backup tests, encryption work). 1 Clari call (UHG/Optum — KMIP for MySQL working, requesting Postgres too). Enterprise encryption dependency.",
    "GCache and WS Encryption": "Zero signal across all sources. No docs page found, no Jira tickets, no Clari mentions. Galera-internal component with no external evidence.",
    "MyRocks": "High Jira activity (63 tickets — signal 11 crashes, assertion failures, gap lock detection, docs, memory instrumentation). Good docs traffic (2,129 views). Zero Clari mentions — engineering-heavy, not sales-facing.",
    "NBO (non-blocking DDLs)": "Minimal evidence. 2 tangential Jira tickets. No docs page, no Clari mentions. PXC-specific DDL feature with little external demand signal.",
    "PXC Scheduler Handler": "Minimal evidence. 1 Jira ticket (security dependency vulnerability). No docs page, no Clari mentions. Internal PXC component.",
    "ProxySQL Admin Scripts": "Moderate docs traffic (3,357 views across ProxySQL pages). Zero Jira tickets directly about admin scripts. No Clari mentions of admin scripts specifically (ProxySQL itself referenced operationally in 2 calls).",
    "Reduced Lock": "1 Clari mention (Coupa — transcription artifact: 'Txp reduced log times'). Zero Jira activity, no docs page found. Minimal evidence.",
}


def compute_evidence_score(data):
    """
    Composite evidence score (0-100) based on:
    - Docs pageviews (0-35 pts): log-scaled, 5000+ = max
    - Jira tickets (0-30 pts): log-scaled, 50+ = max
    - Clari mentions (0-20 pts): 3+ = max (calls are rare per feature)
    - Source diversity bonus (0-15 pts): 5 pts per source with data
    """
    score = 0

    docs = data.get("docs_pageviews_24m")
    if docs and docs > 0:
        score += min(35, 35 * math.log10(docs + 1) / math.log10(5001))

    jira = data.get("jira_ticket_count", 0)
    if jira > 0:
        score += min(30, 30 * math.log10(jira + 1) / math.log10(51))

    clari = data.get("clari_mention_count", 0)
    if clari > 0:
        score += min(20, 20 * (clari / 3))

    sources_with_data = sum([
        1 if (docs and docs > 0) else 0,
        1 if jira > 0 else 0,
        1 if clari > 0 else 0,
    ])
    score += sources_with_data * 5

    return round(min(100, score), 1)


def update():
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    now = datetime.utcnow().isoformat() + "Z"

    for name, data in EVIDENCE.items():
        score = compute_evidence_score(data)
        summary = EVIDENCE_SUMMARIES.get(name, "")

        db.execute("""
            UPDATE cut_keep_features SET
                jira_ticket_count = ?,
                clari_mention_count = ?,
                docs_pageviews_24m = ?,
                evidence_score = ?,
                evidence_summary = ?,
                last_swept_at = ?,
                updated_at = unixepoch()
            WHERE name = ?
        """, (
            data["jira_ticket_count"],
            data["clari_mention_count"],
            data.get("docs_pageviews_24m"),
            score,
            summary,
            now,
            name,
        ))

    db.commit()

    rows = db.execute(
        "SELECT name, evidence_score, jira_ticket_count, clari_mention_count, docs_pageviews_24m "
        "FROM cut_keep_features ORDER BY evidence_score DESC"
    ).fetchall()

    print(f"{'Feature':<45} {'Score':>6} {'Jira':>5} {'Clari':>6} {'Docs':>7}")
    print("-" * 75)
    for r in rows:
        docs = r["docs_pageviews_24m"] or 0
        print(f"{r['name']:<45} {r['evidence_score']:>6.1f} {r['jira_ticket_count']:>5} {r['clari_mention_count']:>6} {docs:>7}")

    db.close()


if __name__ == "__main__":
    update()
