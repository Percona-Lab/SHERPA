"""Update cut_keep_features with evidence from Jira, Clari Copilot, and PostHog sweeps."""

import json
import math
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(os.environ.get("SHERPA_DATA_DIR", str(Path(__file__).parent))) / "portal.db"

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

SEARCH_FOOTPRINT = {
    "LOCK TABLES FOR BACKUP": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects (all issues)", "date_range": "May 2024 – May 2026 (24 months)", "query_terms": ["backup locks", "LOCK TABLES FOR BACKUP", "LOCK BINLOG FOR BACKUP", "have_backup_locks"]},
        "clari": {"corpus": "461 MySQL-tagged Clari Copilot calls (~18 transcripts sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["backup locks", "LOCK TABLES FOR BACKUP"]},
        "posthog": {"corpus": "docs.percona.com pageview events (PostHog EU)", "date_range": "May 2024 – May 2026 (24 months)", "query_terms": ["backup-locks.html"]},
        "telemetry": {"corpus": "Percona install telemetry (vista-data)", "date_range": "24 months", "query_terms": ["have_backup_locks"]},
        "slack": {"corpus": "Not yet searched", "date_range": "N/A", "query_terms": []},
    },
    "Slow query log rotation and expiration": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["slow log rotation", "slowlog rotation", "max_slowlog_size", "max_slowlog_files"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["slow log rotation", "slowlog"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["slowlog-rotation.html"]},
    },
    "PXB estimate memory": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["estimate memory", "xtrabackup memory", "--estimate-memory"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["estimate memory", "xtrabackup memory"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["estimate-memory.html", "xtrabackup-option-reference.html#estimate-memory"]},
    },
    "Utility user": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["utility user", "utility_user", "utility_user_password"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["utility user"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["utility-user.html"]},
    },
    "JS stored procedure": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["JavaScript stored", "JS stored", "JS language plugin", "component_percona_language_service"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["JavaScript stored procedure", "JS stored"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "Jan 2025 – May 2026 (page created Jan 2025)", "query_terms": ["js-lang-overview.html"]},
    },
    "Adaptive network buffers": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["adaptive network buffers", "net_buffer_length_dynamic"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["adaptive network buffers", "network buffer"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["adaptive-network-buffers.html"]},
    },
    "Extended SELECT INTO OUTFILE/DUMPFILE": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["SELECT INTO OUTFILE", "extended OUTFILE", "INTO OUTFILE COMPRESSION"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["SELECT INTO OUTFILE", "OUTFILE compression"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["extended-select-into-outfile.html"]},
    },
    "LDAP Plugin": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["LDAP plugin", "LDAP authentication"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["LDAP"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["ldap-authentication.html"]},
    },
    "MeCAB Plugin": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["MeCAB", "mecab plugin", "mecab phrase"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["MeCAB"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["mecab"]},
    },
    "Audit Log Plugin (Old)": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["audit log plugin", "audit_log", "audit log filter"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["audit log"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["audit-log-plugin.html (8.0)", "audit_log_plugin.html (5.7)"]},
    },
    "Keyring plugins/components": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["keyring plugin", "keyring component", "keyring_file", "keyring_vault", "KMIP"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["keyring", "KMIP"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["using-keyring-plugin.html"]},
    },
    "GCache and WS Encryption": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["gcache", "wsrep encryption", "WS encryption"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["gcache", "wsrep encryption"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["gcache"]},
    },
    "MyRocks": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["MyRocks", "RocksDB"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["MyRocks", "RocksDB"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["install-myrocks.html", "myrocks-index.html"]},
    },
    "NBO (non-blocking DDLs)": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["non-blocking DDL", "NBO", "non-blocking operations"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["non-blocking DDL", "NBO"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["nbo"]},
    },
    "PXC Scheduler Handler": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["scheduler handler", "pxc_scheduler_handler"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["scheduler handler"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["pxc-scheduler"]},
    },
    "ProxySQL Admin Scripts": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["proxysql admin", "proxysql-admin"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["proxysql admin"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["proxysql/index.html"]},
    },
    "Reduced Lock": {
        "jira": {"corpus": "PS, MYR, K8SPS, DISTMYSQL projects", "date_range": "May 2024 – May 2026", "query_terms": ["reduced lock", "LOCK TABLES backup reduced"]},
        "clari": {"corpus": "461 MySQL-tagged calls (~18 sampled)", "date_range": "Sep 2025 – May 2026", "query_terms": ["reduced lock"]},
        "posthog": {"corpus": "docs.percona.com pageviews", "date_range": "May 2024 – May 2026", "query_terms": ["reduced-lock"]},
    },
}

EVIDENCE_ITEMS = {
    "LOCK TABLES FOR BACKUP": {
        "jira": [
            {"id": "PS-9668", "url": "https://perconadev.atlassian.net/browse/PS-9668", "desc": "Crash with audit + LTFB"},
            {"id": "PS-9699", "url": "https://perconadev.atlassian.net/browse/PS-9699", "desc": "Code refresh"},
            {"id": "PS-9559", "url": "https://perconadev.atlassian.net/browse/PS-9559", "desc": "Page tracking"},
        ],
        "posthog": [{"id": "backup-locks.html", "desc": "2,234 pageviews (~93/mo avg)"}],
    },
    "Slow query log rotation and expiration": {
        "jira": [
            {"id": "PS-10128", "url": "https://perconadev.atlassian.net/browse/PS-10128", "desc": "Slow log rotation crash bug"},
            {"id": "PS-9349", "url": "https://perconadev.atlassian.net/browse/PS-9349", "desc": "max_slowlog_size doc improvement"},
            {"id": "PS-9348", "url": "https://perconadev.atlassian.net/browse/PS-9348", "desc": "Doc improvement"},
            {"id": "PS-9347", "url": "https://perconadev.atlassian.net/browse/PS-9347", "desc": "Doc improvement"},
        ],
        "posthog": [{"id": "slowlog-rotation.html", "desc": "1,263 pageviews (~53/mo avg)"}],
    },
    "JS stored procedure": {
        "jira": [
            {"id": "PS-10160", "url": "https://perconadev.atlassian.net/browse/PS-10160", "desc": "Epic: JS Stored Routines GA"},
            {"id": "PS-10113", "url": "https://perconadev.atlassian.net/browse/PS-10113", "desc": "Crash bug"},
            {"id": "PS-10417", "url": "https://perconadev.atlassian.net/browse/PS-10417", "desc": "Memory crash"},
            {"id": "PS-9672", "url": "https://perconadev.atlassian.net/browse/PS-9672", "desc": "Signal 11"},
            {"id": "PS-10427", "url": "https://perconadev.atlassian.net/browse/PS-10427", "desc": "Docs"},
            {"id": "PS-9825", "url": "https://perconadev.atlassian.net/browse/PS-9825", "desc": "Telemetry"},
            {"id": "PS-9826", "url": "https://perconadev.atlassian.net/browse/PS-9826", "desc": "Telemetry"},
            {"id": "MYR-300", "url": "https://perconadev.atlassian.net/browse/MYR-300", "desc": "Idea"},
        ],
        "clari": [{"id": "Coupa call", "desc": "Customer requested JS stored procedures (transcribed as 'Gs start procedures')"}],
        "posthog": [{"id": "js-lang-overview.html", "desc": "202 pageviews since Jan 2025, trending up (39 in Apr 2026)"}],
    },
    "LDAP Plugin": {
        "jira": [
            {"id": "PS-9704", "url": "https://perconadev.atlassian.net/browse/PS-9704", "desc": "LDAP plugin double quotes bug"},
            {"id": "PS-9629", "url": "https://perconadev.atlassian.net/browse/PS-9629", "desc": "LDAP docs review"},
            {"id": "PS-9678", "url": "https://perconadev.atlassian.net/browse/PS-9678", "desc": "Okta auth extension"},
        ],
        "clari": [{"id": "Spinnaker call", "desc": "LDAP mentioned in enterprise authentication requirements"}],
        "posthog": [{"id": "ldap-authentication.html", "desc": "2,027 pageviews (~84/mo avg)"}],
    },
    "MeCAB Plugin": {
        "jira": [
            {"id": "PS-10385", "url": "https://perconadev.atlassian.net/browse/PS-10385", "desc": "Mecab phrase search PR"},
            {"id": "PS-10383", "url": "https://perconadev.atlassian.net/browse/PS-10383", "desc": "Mecab phrase adjacency bug"},
            {"id": "PS-10378", "url": "https://perconadev.atlassian.net/browse/PS-10378", "desc": "Mecab boolean mode optimization bug"},
        ],
    },
    "Audit Log Plugin (Old)": {
        "jira": [
            {"id": "PS-9369", "url": "https://perconadev.atlassian.net/browse/PS-9369", "desc": "Memory leak"},
            {"id": "PS-9668", "url": "https://perconadev.atlassian.net/browse/PS-9668", "desc": "Crash with LTFB"},
            {"id": "PS-10129", "url": "https://perconadev.atlassian.net/browse/PS-10129", "desc": "Crash with validate_password"},
            {"id": "PS-10873", "url": "https://perconadev.atlassian.net/browse/PS-10873", "desc": "Charset test failure"},
            {"title": "+ 82 more", "desc": "Filter improvements, JSONL format, regex filters, docs"},
        ],
        "clari": [
            {"id": "Coupa call", "desc": "Detailed discussion of audit log plugin deprecation and workarounds for 8.4"},
            {"id": "Arista Networks call", "desc": "Audit log mentioned in onboarding"},
            {"id": "Choice Home call", "desc": "Audit log exclusion settings ticket"},
        ],
        "posthog": [{"id": "audit-log-plugin.html", "desc": "12,913 pageviews (~538/mo avg across 8.0 + 5.7 pages)"}],
    },
    "Keyring plugins/components": {
        "jira": [
            {"id": "PS-9673", "url": "https://perconadev.atlassian.net/browse/PS-9673", "desc": "KMIP crash"},
            {"id": "PS-10080", "url": "https://perconadev.atlassian.net/browse/PS-10080", "desc": "KMIP backup tests"},
            {"id": "DISTMYSQL-510", "url": "https://perconadev.atlassian.net/browse/DISTMYSQL-510", "desc": "Vault backup error"},
            {"title": "+ 30 more", "desc": "Encryption work, KMIP, vault, component migration"},
        ],
        "clari": [{"id": "UHG/Optum call", "desc": "Extensive KMIP discussion — MySQL KMIP working, requesting KMIP for Postgres"}],
        "posthog": [{"id": "using-keyring-plugin.html", "desc": "1,808 pageviews (~75/mo avg)"}],
    },
    "MyRocks": {
        "jira": [
            {"id": "PS-9846", "url": "https://perconadev.atlassian.net/browse/PS-9846", "desc": "Signal 11 crash"},
            {"id": "PS-9842", "url": "https://perconadev.atlassian.net/browse/PS-9842", "desc": "Assertion failure"},
            {"id": "PS-10596", "url": "https://perconadev.atlassian.net/browse/PS-10596", "desc": "Docs part 3"},
            {"id": "PS-10098", "url": "https://perconadev.atlassian.net/browse/PS-10098", "desc": "Gap lock detection"},
            {"id": "PS-9664", "url": "https://perconadev.atlassian.net/browse/PS-9664", "desc": "Memory instrumentation"},
            {"title": "+ 58 more", "desc": "Bugs, improvements, RocksDB tag merges"},
        ],
        "posthog": [{"id": "myrocks pages", "desc": "2,129 pageviews across install-myrocks.html + myrocks-index.html"}],
    },
    "NBO (non-blocking DDLs)": {
        "jira": [
            {"title": "~2 tangential", "desc": "No issues directly about NBO; matches on 'non-blocking' in lock/DDL contexts"},
        ],
    },
    "PXC Scheduler Handler": {
        "jira": [
            {"id": "DISTMYSQL-476", "url": "https://perconadev.atlassian.net/browse/DISTMYSQL-476", "desc": "pxc_scheduler_handler DoS vulnerability in logrus dependency"},
        ],
    },
    "Reduced Lock": {
        "clari": [{"id": "Coupa call", "desc": "Summary references 'Txp reduced log times' — likely transcription of 'reduced lock times'"}],
    },
    "ProxySQL Admin Scripts": {
        "posthog": [{"id": "proxysql pages", "desc": "3,357 pageviews across ProxySQL doc pages (not specific to admin scripts)"}],
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
    now = datetime.now(timezone.utc).isoformat()

    for name, data in EVIDENCE.items():
        score = compute_evidence_score(data)
        summary = EVIDENCE_SUMMARIES.get(name, "")
        footprint = SEARCH_FOOTPRINT.get(name, {})
        items = EVIDENCE_ITEMS.get(name, {})

        db.execute("""
            UPDATE cut_keep_features SET
                jira_ticket_count = ?,
                clari_mention_count = ?,
                docs_pageviews_24m = ?,
                evidence_score = ?,
                evidence_summary = ?,
                evidence_items = ?,
                search_footprint = ?,
                last_swept_at = ?,
                updated_at = unixepoch()
            WHERE name = ?
        """, (
            data["jira_ticket_count"],
            data["clari_mention_count"],
            data.get("docs_pageviews_24m"),
            score,
            summary,
            json.dumps(items),
            json.dumps(footprint),
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
