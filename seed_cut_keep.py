"""Seed the cut_keep_features table with v0 scope from the Evidence Sweep methodology doc."""

import json
import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "portal.db"

V0_FEATURES = [
    {
        "name": "LOCK TABLES FOR BACKUP",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/backup-locks.html",
        "telemetry_status": "Unknown",
        "aliases": ["backup locks", "LOCK TABLES FOR BACKUP", "LOCK BINLOG FOR BACKUP"],
        "variables": ["have_backup_locks", "LOCK TABLES FOR BACKUP", "LOCK BINLOG FOR BACKUP"],
        "negative_terms": ["mysqldump", "upstream LOCK TABLES"],
    },
    {
        "name": "Slow query log rotation and expiration",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/slowlog-rotation.html",
        "telemetry_status": "Unknown",
        "aliases": ["slow log rotation", "slow query log expiration", "slowlog rotation"],
        "variables": ["max_slowlog_size", "max_slowlog_files", "slow_query_log_use_global_control"],
        "negative_terms": [],
    },
    {
        "name": "PXB estimate memory",
        "area": "PXB",
        "doc_url": "https://docs.percona.com/percona-xtrabackup/8.4/estimate-memory.html",
        "telemetry_status": "Unknown",
        "aliases": ["xtrabackup estimate memory", "PXB memory estimate", "estimate-memory"],
        "variables": ["--estimate-memory"],
        "negative_terms": [],
    },
    {
        "name": "Utility user",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/utility-user.html",
        "telemetry_status": "Unknown",
        "aliases": ["utility user", "utility_user"],
        "variables": ["utility_user", "utility_user_password", "utility_user_schema_access",
                      "utility_user_dynamic_privileges"],
        "negative_terms": [],
    },
    {
        "name": "JS stored procedure",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/js-lang-overview.html",
        "telemetry_status": "Unknown",
        "aliases": ["JavaScript stored procedures", "JS stored programs", "JS language plugin",
                    "CREATE FUNCTION ... LANGUAGE JAVASCRIPT"],
        "variables": ["component_percona_language_service"],
        "negative_terms": ["Node.js", "V8 engine upstream"],
    },
    {
        "name": "Adaptive network buffers",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/adaptive-network-buffers.html",
        "telemetry_status": "Yes",
        "aliases": ["adaptive network buffers", "network buffer sizing"],
        "variables": ["net_buffer_length_dynamic"],
        "negative_terms": ["net_buffer_length upstream"],
    },
    {
        "name": "Extended SELECT INTO OUTFILE/DUMPFILE",
        "area": "PS",
        "doc_url": "https://docs.percona.com/percona-server/8.4/extended-select-into-outfile.html",
        "telemetry_status": "Yes",
        "aliases": ["extended SELECT INTO OUTFILE", "SELECT INTO DUMPFILE compression",
                    "extended OUTFILE"],
        "variables": ["INTO OUTFILE ... COMPRESSION"],
        "negative_terms": ["upstream SELECT INTO"],
    },
]

CANDIDATE_ADDITIONS = [
    {"name": "LDAP Plugin", "area": "PS"},
    {"name": "MeCAB Plugin", "area": "PS"},
    {"name": "Audit Log Plugin (Old)", "area": "PS"},
    {"name": "Keyring plugins/components", "area": "PS"},
    {"name": "GCache and WS Encryption", "area": "PXC"},
    {"name": "MyRocks", "area": "PS"},
    {"name": "NBO (non-blocking DDLs)", "area": "PXC"},
    {"name": "PXC Scheduler Handler", "area": "PXC"},
    {"name": "ProxySQL Admin Scripts", "area": "ProxySQL"},
    {"name": "Reduced Lock", "area": "PS"},
]


def make_id(name):
    return "ck-" + hashlib.sha256(name.encode()).hexdigest()[:12]


def seed():
    db = sqlite3.connect(str(DB_PATH))

    for feat in V0_FEATURES:
        fid = make_id(feat["name"])
        db.execute("""
            INSERT OR IGNORE INTO cut_keep_features
            (id, name, area, tech, status, doc_url, aliases, variables,
             negative_terms, telemetry_status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            fid, feat["name"], feat["area"], "MySQL", "Unknown",
            feat.get("doc_url", ""),
            json.dumps(feat.get("aliases", [])),
            json.dumps(feat.get("variables", [])),
            json.dumps(feat.get("negative_terms", [])),
            feat.get("telemetry_status", "Unknown"),
        ))

    for feat in CANDIDATE_ADDITIONS:
        fid = make_id(feat["name"])
        db.execute("""
            INSERT OR IGNORE INTO cut_keep_features
            (id, name, area, tech, status, doc_url, aliases, variables,
             negative_terms, telemetry_status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            fid, feat["name"], feat["area"], "MySQL", "Unknown",
            "", "[]", "[]", "[]", "Unknown",
        ))

    db.commit()
    count = db.execute("SELECT COUNT(*) FROM cut_keep_features").fetchone()[0]
    print(f"Seeded {count} cut/keep features")
    db.close()


if __name__ == "__main__":
    seed()
