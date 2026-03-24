"""
SHERPA — Stakeholder Hub for Enhancement Request Prioritization & Action
Domain-based auth (internal), with optional email verification for customers later.
"""

import hmac
import os
import sqlite3
import time
from functools import wraps
from pathlib import Path

import logging
from dotenv import load_dotenv
import requests
from flask import Flask, g, jsonify, redirect, request, send_from_directory

load_dotenv(Path.home() / ".percona-portal.env")

app = Flask(__name__, static_folder="static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600  # Cache static assets for 1 hour

# ─── Configuration ───
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
NOTION_VERSION = "2022-06-28"

ADMIN_KEY = os.environ.get("PORTAL_ADMIN_KEY", "")

# Auth: comma-separated allowed domains. Empty = allow all (with email verification later)
ALLOWED_DOMAINS = [d.strip().lower() for d in os.environ.get("ALLOWED_DOMAINS", "percona.com").split(",") if d.strip()]
# When True, allowed domains skip email verification. Others need verification (future).
DOMAIN_TRUST_MODE = True

_DATA_DIR = Path(os.environ.get("SHERPA_DATA_DIR", str(Path(__file__).parent)))
DB_PATH = _DATA_DIR / "portal.db"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

STATE_MAP = {
    "Ideation": "Under Consideration",
    "Feasibility Check": "Under Consideration",
    "Warming Up": "Under Consideration",
    "Prioritised": "Planned",
    "Committed": "Planned",
    "Implementation": "In Progress",
    "Success": "Shipped",
}
HIDDEN_STATES = {"Rejected", "Failure", "Gone Bad"}
IMPORTANCE_LEVELS = {"nice_to_have", "important", "critical"}


# ─── Database ───
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def init_db():
    db = sqlite3.connect(str(DB_PATH))
    db.executescript("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            display_name TEXT DEFAULT '',
            verified INTEGER DEFAULT 0,
            created_at REAL DEFAULT (unixepoch()),
            last_active_at REAL DEFAULT (unixepoch()),
            is_blocked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id INTEGER NOT NULL REFERENCES voters(id),
            feature_id TEXT NOT NULL,
            importance TEXT DEFAULT 'important',
            customer_name TEXT DEFAULT '',
            created_at REAL DEFAULT (unixepoch()),
            UNIQUE(voter_id, feature_id)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id INTEGER NOT NULL REFERENCES voters(id),
            feature_id TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at REAL DEFAULT (unixepoch()),
            is_removed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS feature_descriptions (
            feature_id TEXT PRIMARY KEY,
            description TEXT DEFAULT '',
            updated_at REAL DEFAULT (unixepoch())
        );
        CREATE INDEX IF NOT EXISTS idx_votes_feature ON votes(feature_id);
        CREATE INDEX IF NOT EXISTS idx_comments_feature ON comments(feature_id);
        CREATE INDEX IF NOT EXISTS idx_voters_email ON voters(email);
    """)
    # Migration: add customer_name if missing (for existing DBs)
    try:
        db.execute("ALTER TABLE votes ADD COLUMN customer_name TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # already exists
    db.close()


# ─── Helpers ───
def require_admin(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        key = request.headers.get("X-Admin-Key", "")
        if not hmac.compare_digest(key, ADMIN_KEY):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapped


def get_verified_voter():
    token = request.headers.get("X-Voter-Token", "")
    if not token:
        return None
    db = get_db()
    return db.execute(
        "SELECT * FROM voters WHERE id = ? AND verified = 1 AND is_blocked = 0",
        (token,),
    ).fetchone()


def is_trusted_domain(email):
    if not ALLOWED_DOMAINS:
        return False
    domain = email.split("@")[-1].lower()
    return domain in ALLOWED_DOMAINS


# ─── Routes: Rybbit Analytics Proxy ───
# Rybbit script.js derives analyticsHost from its own src path.
# With src="/rybbit/script.js", analyticsHost = "/rybbit" and it sends to /rybbit/track, /rybbit/site/*, etc.
RYBBIT_BACKEND = "http://127.0.0.1:3003"

@app.route("/rybbit/script.js")
def rybbit_script():
    resp = requests.get(f"{RYBBIT_BACKEND}/script.js", timeout=5)
    return resp.content, resp.status_code, {"Content-Type": "application/javascript", "Cache-Control": "public, max-age=3600"}

@app.route("/rybbit/<path:path>", methods=["GET", "POST"])
def rybbit_proxy(path):
    # Rybbit registers all endpoints under /api/ but the script sends without the prefix
    url = f"{RYBBIT_BACKEND}/api/{path}"
    if request.method == "POST":
        resp = requests.post(url, data=request.get_data(), headers={"Content-Type": request.content_type or "application/json"}, timeout=10)
    else:
        resp = requests.get(url, params=request.args, timeout=10)
    return resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")}

# ─── Routes: Static ───
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/portal")
def portal_page():
    return redirect("/")

@app.route("/admin")
def admin_page():
    return send_from_directory("static", "admin.html")

@app.route("/signals")
def signals_page():
    return send_from_directory("static", "signals.html")

@app.route("/signals/<signal_id>")
def signal_detail_page(signal_id):
    return send_from_directory("static", "signal-detail.html")

@app.route("/evidence")
def evidence_page():
    return send_from_directory("static", "evidence.html")


# ─── Routes: Features ───
@app.route("/api/features")
def get_features():
    payload = {
        "filter": {"property": "Publish to Portal", "checkbox": {"equals": True}},
        "sorts": [{"property": "Name", "direction": "ascending"}],
    }

    # Paginate through all Notion results
    all_pages = []
    has_more = True
    while has_more:
        try:
            resp = requests.post(
                f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
                headers=NOTION_HEADERS, json=payload, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 502
        all_pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        if has_more:
            payload["start_cursor"] = data["next_cursor"]

    db = get_db()
    voter = get_verified_voter()
    features = []

    for page in all_pages:
        props = page["properties"]
        page_id = page["id"]

        ps_obj = props.get("Planning State", {})
        planning_state = ps_obj.get("status", {}).get("name", "") if ps_obj.get("status") else ""
        if planning_state in HIDDEN_STATES:
            continue

        po_obj = props.get("Portal Status", {})
        portal_status = po_obj.get("select", {}).get("name", "") if po_obj.get("select") else ""
        display_status = portal_status or STATE_MAP.get(planning_state, "Under Consideration")

        name_obj = props.get("Name", {})
        name = "".join(t.get("plain_text", "") for t in name_obj.get("title", [])) if name_obj.get("type") == "title" else ""

        # Description: prefer local DB, fall back to Notion Portal Description
        local_desc_row = db.execute("SELECT description FROM feature_descriptions WHERE feature_id=?", (page_id,)).fetchone()
        if local_desc_row and local_desc_row["description"]:
            description = local_desc_row["description"]
        else:
            desc_obj = props.get("Portal Description", {})
            description = "".join(t.get("plain_text", "") for t in desc_obj.get("rich_text", [])) if desc_obj.get("type") == "rich_text" else ""

        db_tech_obj = props.get("DB Tech", {})
        db_tech = [o["name"] for o in db_tech_obj.get("multi_select", [])] if db_tech_obj.get("type") == "multi_select" else []

        vote_count = db.execute("SELECT COUNT(*) as cnt FROM votes WHERE feature_id=?", (page_id,)).fetchone()["cnt"]
        importance = dict(db.execute("SELECT importance, COUNT(*) as cnt FROM votes WHERE feature_id=? GROUP BY importance", (page_id,)).fetchall())
        comment_count = db.execute("SELECT COUNT(*) as cnt FROM comments WHERE feature_id=? AND is_removed=0", (page_id,)).fetchone()["cnt"]

        my_vote = None
        my_customer = ""
        if voter:
            mv = db.execute("SELECT importance, customer_name FROM votes WHERE voter_id=? AND feature_id=?", (voter["id"], page_id)).fetchone()
            if mv:
                my_vote = mv["importance"]
                my_customer = mv["customer_name"] or ""

        # Notion page URL
        notion_url = f"https://www.notion.so/{page_id.replace('-', '')}"

        features.append({
            "id": page_id, "name": name, "description": description,
            "db_tech": db_tech, "status": display_status, "votes": vote_count,
            "importance": {
                "nice_to_have": importance.get("nice_to_have", 0),
                "important": importance.get("important", 0),
                "critical": importance.get("critical", 0),
            },
            "my_vote": my_vote, "my_customer": my_customer,
            "comment_count": comment_count,
            "notion_url": notion_url,
        })

    return jsonify(features)


# ─── Routes: Auth (domain-based) ───
@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    display_name = (body.get("display_name") or "").strip()

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "Valid email required"}), 400

    if not display_name:
        return jsonify({"error": "Name is required"}), 400

    if DOMAIN_TRUST_MODE and ALLOWED_DOMAINS and not is_trusted_domain(email):
        domains = ", ".join(ALLOWED_DOMAINS)
        return jsonify({"error": f"Only @{domains} emails are allowed. Customer access coming soon!"}), 403

    db = get_db()
    voter = db.execute("SELECT * FROM voters WHERE email=?", (email,)).fetchone()

    if voter and voter["is_blocked"]:
        return jsonify({"error": "This account has been blocked"}), 403

    if voter:
        db.execute("UPDATE voters SET display_name=?, verified=1, last_active_at=? WHERE id=?",
                    (display_name, time.time(), voter["id"]))
        db.commit()
        voter_id = voter["id"]
    else:
        cur = db.execute("INSERT INTO voters (email, display_name, verified) VALUES (?,?,1)",
                         (email, display_name))
        db.commit()
        voter_id = cur.lastrowid

    return jsonify({
        "ok": True,
        "voter_id": voter_id,
        "email": email,
        "display_name": display_name,
    })


@app.route("/api/auth/check")
def check_auth():
    voter = get_verified_voter()
    if voter:
        return jsonify({"authenticated": True, "voter_id": voter["id"],
                        "email": voter["email"], "display_name": voter["display_name"]})
    return jsonify({"authenticated": False})


# ─── Routes: Voting ───
@app.route("/api/vote", methods=["POST"])
def vote():
    voter = get_verified_voter()
    if not voter:
        return jsonify({"error": "auth_required"}), 401

    body = request.get_json(silent=True) or {}
    feature_id = body.get("feature_id")
    importance = body.get("importance", "important")
    customer_name = (body.get("customer_name") or "").strip()
    action = body.get("action", "upvote")

    if not feature_id:
        return jsonify({"error": "feature_id required"}), 400
    if importance not in IMPORTANCE_LEVELS:
        return jsonify({"error": "Invalid importance"}), 400

    db = get_db()
    if action == "remove":
        db.execute("DELETE FROM votes WHERE voter_id=? AND feature_id=?", (voter["id"], feature_id))
    else:
        db.execute(
            """INSERT INTO votes (voter_id, feature_id, importance, customer_name)
               VALUES (?,?,?,?)
               ON CONFLICT(voter_id, feature_id) DO UPDATE SET importance=excluded.importance, customer_name=excluded.customer_name""",
            (voter["id"], feature_id, importance, customer_name),
        )
    db.execute("UPDATE voters SET last_active_at=? WHERE id=?", (time.time(), voter["id"]))
    db.commit()

    count = db.execute("SELECT COUNT(*) as cnt FROM votes WHERE feature_id=?", (feature_id,)).fetchone()["cnt"]

    # SHERPA Demand Engine: fire signal ingestion (non-blocking, best-effort)
    if action != "remove":
        try:
            from demand.ingestion import handle_vote_event
            tallies_rows = db.execute(
                "SELECT importance, COUNT(*) as cnt FROM votes WHERE feature_id=? GROUP BY importance",
                (feature_id,),
            ).fetchall()
            tallies = {
                "total": count,
                "critical": 0, "important": 0, "nice_to_have": 0,
            }
            for r in tallies_rows:
                tallies[r["importance"]] = r["cnt"]
            handle_vote_event(
                feature_id=feature_id,
                feature_title=body.get("feature_title", ""),
                voter_email=voter["email"],
                voter_display_name=voter.get("display_name"),
                importance=importance,
                tallies=tallies,
                notion_url=f"https://www.notion.so/{feature_id.replace('-', '')}",
            )
        except Exception as e:
            app.logger.warning(f"Demand engine ingestion failed (non-blocking): {e}")

    return jsonify({"ok": True, "votes": count})


# ─── Routes: Comments ───
@app.route("/api/comments/<feature_id>")
def get_comments(feature_id):
    db = get_db()
    rows = db.execute(
        """SELECT c.id, c.body, c.created_at, v.display_name, v.email
           FROM comments c JOIN voters v ON c.voter_id=v.id
           WHERE c.feature_id=? AND c.is_removed=0 ORDER BY c.created_at ASC""",
        (feature_id,),
    ).fetchall()

    return jsonify([{
        "id": r["id"], "body": r["body"],
        "display_name": r["display_name"] or r["email"].split("@")[0],
        "created_at": r["created_at"],
    } for r in rows])


@app.route("/api/comments", methods=["POST"])
def post_comment():
    voter = get_verified_voter()
    if not voter:
        return jsonify({"error": "auth_required"}), 401

    body = request.get_json(silent=True) or {}
    feature_id = body.get("feature_id")
    text = (body.get("body") or "").strip()

    if not feature_id or not text:
        return jsonify({"error": "feature_id and body required"}), 400
    if len(text) > 2000:
        return jsonify({"error": "Comment too long (max 2000 chars)"}), 400

    db = get_db()
    db.execute("INSERT INTO comments (voter_id, feature_id, body) VALUES (?,?,?)", (voter["id"], feature_id, text))
    db.execute("UPDATE voters SET last_active_at=? WHERE id=?", (time.time(), voter["id"]))
    db.commit()

    # SHERPA Demand Engine: fire signal ingestion for comment (non-blocking, best-effort)
    try:
        from demand.ingestion import handle_comment_event
        vote_count = db.execute("SELECT COUNT(*) as cnt FROM votes WHERE feature_id=?", (feature_id,)).fetchone()["cnt"]
        tallies_rows = db.execute(
            "SELECT importance, COUNT(*) as cnt FROM votes WHERE feature_id=? GROUP BY importance",
            (feature_id,),
        ).fetchall()
        tallies = {
            "total": vote_count,
            "critical": 0, "important": 0, "nice_to_have": 0,
        }
        for r in tallies_rows:
            tallies[r["importance"]] = r["cnt"]
        handle_comment_event(
            feature_id=feature_id,
            feature_title=body.get("feature_title", ""),
            voter_email=voter["email"],
            voter_display_name=voter.get("display_name"),
            comment_text=text,
            tallies=tallies,
            notion_url=f"https://www.notion.so/{feature_id.replace('-', '')}",
        )
    except Exception as e:
        app.logger.warning(f"Demand engine comment ingestion failed (non-blocking): {e}")

    return jsonify({"ok": True})


# ─── Routes: Admin ───
@app.route("/api/admin/votes")
@require_admin
def admin_votes():
    db = get_db()
    rows = db.execute(
        """SELECT v.id as vote_id, v.feature_id, v.importance, v.customer_name, v.created_at,
                  vt.email, vt.display_name, vt.is_blocked
           FROM votes v JOIN voters vt ON v.voter_id=vt.id ORDER BY v.created_at DESC LIMIT 500"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/comments")
@require_admin
def admin_comments():
    db = get_db()
    rows = db.execute(
        """SELECT c.id, c.feature_id, c.body, c.created_at, c.is_removed,
                  vt.email, vt.display_name
           FROM comments c JOIN voters vt ON c.voter_id=vt.id ORDER BY c.created_at DESC LIMIT 500"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/voters")
@require_admin
def admin_voters():
    db = get_db()
    rows = db.execute(
        """SELECT vt.id, vt.email, vt.display_name, vt.verified, vt.is_blocked,
                  vt.created_at, vt.last_active_at,
                  COUNT(DISTINCT v.id) as vote_count,
                  COUNT(DISTINCT c.id) as comment_count
           FROM voters vt LEFT JOIN votes v ON v.voter_id=vt.id
           LEFT JOIN comments c ON c.voter_id=vt.id AND c.is_removed=0
           GROUP BY vt.id ORDER BY vt.last_active_at DESC LIMIT 500"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/vote/<int:vote_id>", methods=["DELETE"])
@require_admin
def admin_delete_vote(vote_id):
    db = get_db()
    db.execute("DELETE FROM votes WHERE id=?", (vote_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/comment/<int:comment_id>", methods=["DELETE"])
@require_admin
def admin_remove_comment(comment_id):
    db = get_db()
    db.execute("UPDATE comments SET is_removed=1 WHERE id=?", (comment_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/voter/<int:voter_id>/block", methods=["POST"])
@require_admin
def admin_block_voter(voter_id):
    body = request.get_json(silent=True) or {}
    block = body.get("block", True)
    db = get_db()
    db.execute("UPDATE voters SET is_blocked=? WHERE id=?", (1 if block else 0, voter_id))
    if block:
        db.execute("DELETE FROM votes WHERE voter_id=?", (voter_id,))
        db.execute("UPDATE comments SET is_removed=1 WHERE voter_id=?", (voter_id,))
    db.commit()
    return jsonify({"ok": True})


# ─── Routes: Admin Features & Summaries ───
@app.route("/api/admin/features")
@require_admin
def admin_features():
    """Return all portal features with vote stats and current summaries."""
    payload = {
        "filter": {"property": "Publish to Portal", "checkbox": {"equals": True}},
        "sorts": [{"property": "Name", "direction": "ascending"}],
    }

    # Paginate through all Notion results
    all_pages = []
    has_more = True
    while has_more:
        try:
            resp = requests.post(
                f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
                headers=NOTION_HEADERS, json=payload, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 502
        all_pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        if has_more:
            payload["start_cursor"] = data["next_cursor"]

    db = get_db()
    features = []
    for page in all_pages:
        props = page["properties"]
        page_id = page["id"]

        name_obj = props.get("Name", {})
        name = "".join(t.get("plain_text", "") for t in name_obj.get("title", [])) if name_obj.get("type") == "title" else ""

        # Description: prefer local DB, fall back to Notion Portal Description
        local_desc_row = db.execute("SELECT description FROM feature_descriptions WHERE feature_id=?", (page_id,)).fetchone()
        if local_desc_row and local_desc_row["description"]:
            description = local_desc_row["description"]
        else:
            desc_obj = props.get("Portal Description", {})
            description = "".join(t.get("plain_text", "") for t in desc_obj.get("rich_text", [])) if desc_obj.get("type") == "rich_text" else ""

        db_tech_obj = props.get("DB Tech", {})
        db_tech = [o["name"] for o in db_tech_obj.get("multi_select", [])] if db_tech_obj.get("type") == "multi_select" else []

        vote_count = db.execute("SELECT COUNT(*) as cnt FROM votes WHERE feature_id=?", (page_id,)).fetchone()["cnt"]
        comment_count = db.execute("SELECT COUNT(*) as cnt FROM comments WHERE feature_id=? AND is_removed=0", (page_id,)).fetchone()["cnt"]

        # Gather voter comments for context
        comments_rows = db.execute(
            "SELECT body FROM comments WHERE feature_id=? AND is_removed=0 ORDER BY created_at DESC LIMIT 20",
            (page_id,),
        ).fetchall()
        recent_comments = [r["body"] for r in comments_rows]

        # Gather customer names from votes
        customer_rows = db.execute(
            "SELECT DISTINCT customer_name FROM votes WHERE feature_id=? AND customer_name != ''", (page_id,),
        ).fetchall()
        customers = [r["customer_name"] for r in customer_rows]

        features.append({
            "id": page_id, "name": name, "description": description,
            "db_tech": db_tech, "votes": vote_count, "comment_count": comment_count,
            "recent_comments": recent_comments,
            "customers": customers,
            "notion_url": f"https://www.notion.so/{page_id.replace('-', '')}",
        })

    return jsonify(features)


@app.route("/api/admin/generate-description/<feature_id>", methods=["POST"])
@require_admin
def generate_description(feature_id):
    """Fetch Notion page content and generate a portal description using Claude."""
    body = request.get_json(silent=True) or {}
    feature_name = body.get("name", "")

    # 1. Fetch all blocks from the Notion page to get the full content
    page_content = _fetch_notion_page_content(feature_id)
    if not page_content:
        return jsonify({"error": "Could not fetch page content from Notion"}), 502

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        # Fallback: just use first ~300 chars of page content
        return jsonify({"ok": True, "description": page_content[:300].strip()})

    prompt = f"""You are writing a short public-facing description for a feature on Percona's internal SHERPA portal (Stakeholder Hub for Enhancement Request Prioritization & Action). This portal lets Percona employees vote on features based on customer and market needs.

Write a concise 2-3 sentence description that:
- Explains the customer/market problem this feature solves
- Describes the value it delivers
- Is written for an internal audience who understands databases

Feature name: {feature_name}
Full Notion page content:
{page_content[:3000]}

Write ONLY the description. No labels, headers, or markdown."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 250,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        description = resp.json()["content"][0]["text"].strip()
        return jsonify({"ok": True, "description": description})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {e}"}), 500


@app.route("/api/admin/save-description/<feature_id>", methods=["POST"])
@require_admin
def save_description(feature_id):
    """Save description to local SQLite."""
    body = request.get_json(silent=True) or {}
    description = (body.get("description") or "").strip()
    if not description:
        return jsonify({"error": "description required"}), 400

    db = get_db()
    db.execute(
        """INSERT INTO feature_descriptions (feature_id, description, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(feature_id) DO UPDATE SET description=excluded.description, updated_at=excluded.updated_at""",
        (feature_id, description, time.time()),
    )
    db.commit()
    return jsonify({"ok": True})


# ─── Routes: SHERPA Demand Engine ───
@app.route("/api/sherpa/ingest", methods=["POST"])
def sherpa_ingest():
    """Ingest evidence from external sources (Slack, Jira, forums, etc.)"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    try:
        from demand.ingestion import ingest_evidence
        result = ingest_evidence(data)
        return jsonify(result.to_dict()), 200
    except Exception as e:
        app.logger.error(f"Demand engine ingest error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/signals")
def sherpa_signals():
    """List all demand signals."""
    try:
        from demand.git_sync import GitSyncManager
        manager = GitSyncManager()
        signals = manager.load_all_signals()
        return jsonify({
            "count": len(signals),
            "signals": [s.to_dict() for s in signals],
        }), 200
    except Exception as e:
        app.logger.error(f"Demand engine signals error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/signals/<signal_id>")
def sherpa_signal_detail(signal_id):
    """Get a single demand signal with all evidence."""
    try:
        from demand.git_sync import GitSyncManager
        manager = GitSyncManager()
        signal = manager.load_signal(signal_id)
        if not signal:
            return jsonify({"error": "Signal not found"}), 404
        return jsonify(signal.to_dict()), 200
    except Exception as e:
        app.logger.error(f"Demand engine signal error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/demand-signals")
def sherpa_demand_signals():
    """Fetch all demand signals from Notion (cached)."""
    try:
        from demand.notion_sync import get_demand_signals_cached
        signals = get_demand_signals_cached()
        return jsonify({"count": len(signals), "signals": signals}), 200
    except Exception as e:
        app.logger.error(f"Demand signals fetch error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/demand-signals/<signal_id>")
def sherpa_demand_signal_detail(signal_id):
    """Fetch a single demand signal with linked evidence."""
    try:
        from demand.notion_sync import get_signal_with_evidence
        signal = get_signal_with_evidence(signal_id)
        if not signal:
            return jsonify({"error": "Signal not found"}), 404
        return jsonify(signal), 200
    except Exception as e:
        app.logger.error(f"Demand signal detail error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/customer-evidence")
def sherpa_customer_evidence():
    """Fetch all customer evidence from Notion (cached)."""
    try:
        from demand.notion_sync import get_customer_evidence_cached
        evidence = get_customer_evidence_cached()
        return jsonify({"count": len(evidence), "evidence": evidence}), 200
    except Exception as e:
        app.logger.error(f"Customer evidence fetch error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/cache/invalidate", methods=["POST"])
@require_admin
def sherpa_invalidate_cache():
    """Force-refresh Notion cache."""
    try:
        from demand.notion_sync import invalidate_cache
        invalidate_cache()
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sherpa/notion-status")
def sherpa_notion_status():
    """Check if Notion sync is configured and working."""
    has_key = bool(os.environ.get("NOTION_API_KEY"))
    if not has_key:
        return jsonify({"status": "unconfigured", "message": "NOTION_API_KEY not set"}), 200
    try:
        from demand.notion_sync import get_all_signals, DEMAND_SIGNALS_DB, CUSTOMER_EVIDENCE_DB
        signals = get_all_signals()
        return jsonify({
            "status": "ok",
            "signal_count": len(signals),
            "databases": {
                "demand_signals": DEMAND_SIGNALS_DB,
                "customer_evidence": CUSTOMER_EVIDENCE_DB,
            },
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def _fetch_notion_page_content(page_id):
    """Fetch all blocks from a Notion page and return as plain text."""
    blocks_text = []
    cursor = None
    for _ in range(5):  # max 5 pages of blocks
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        try:
            resp = requests.get(url, headers=NOTION_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException:
            break

        for block in data.get("results", []):
            block_type = block.get("type", "")
            block_data = block.get(block_type, {})
            # Extract text from rich_text arrays in common block types
            rich_text = block_data.get("rich_text", [])
            if rich_text:
                text = "".join(t.get("plain_text", "") for t in rich_text)
                if text.strip():
                    blocks_text.append(text.strip())
            # Handle to-do items
            if block_type == "to_do":
                checked = block_data.get("checked", False)
                prefix = "[x]" if checked else "[ ]"
                text = "".join(t.get("plain_text", "") for t in block_data.get("rich_text", []))
                if text.strip():
                    blocks_text.append(f"{prefix} {text.strip()}")

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return "\n".join(blocks_text)


# ─── @sherpa Slack Bot ───
try:
    from bot.handlers import create_slack_app
    slack_app = create_slack_app()
    if slack_app:
        from slack_bolt.adapter.flask import SlackRequestHandler
        slack_handler = SlackRequestHandler(slack_app)

        @app.route("/slack/events", methods=["POST"])
        def slack_events():
            return slack_handler.handle(request)

        @app.route("/slack/commands", methods=["POST"])
        def slack_commands():
            return slack_handler.handle(request)
except Exception as e:
    logging.getLogger(__name__).info(f"Slack bot not loaded: {e}")


# ─── Proactive Monitoring (scheduler) ───
if os.getenv("SLACK_BOT_TOKEN"):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler()

        def weekly_digest_job():
            """Runs Monday 9 AM — posts weekly digest to #sherpa-signals."""
            try:
                from bot.notifications import format_weekly_digest, send_to_channel
                from demand.notion_sync import get_all_signals
                signals = get_all_signals()
                digest = format_weekly_digest(
                    new_signals=len(signals),
                    merged_count=0,
                    pending_reviews=0,
                    top_movers=[],
                )
                send_to_channel(digest.get("blocks", []))
            except Exception as e:
                logging.getLogger(__name__).warning(f"Weekly digest failed: {e}")

        def anomaly_scan_job():
            """Runs every 4 hours — checks for demand spikes, clusters, churn signals."""
            try:
                from bot.notifications import format_anomaly_alert, send_to_channel
                from demand.notion_sync import get_all_signals
                # TODO: Compare current scores to last snapshot
                # Alert if: score jumps >10 pts, 3+ customers same topic in a week,
                # new churn signal, 5+ evidence in 48 hours
            except Exception as e:
                logging.getLogger(__name__).warning(f"Anomaly scan failed: {e}")

        scheduler.add_job(weekly_digest_job, 'cron', day_of_week='mon', hour=9)
        scheduler.add_job(anomaly_scan_job, 'interval', hours=4)
        scheduler.start()
    except ImportError:
        logging.getLogger(__name__).info("APScheduler not installed — proactive monitoring disabled")


if __name__ == "__main__":
    init_db()
    if not DATABASE_ID:
        print("  WARNING: NOTION_DATABASE_ID not set — features will not load")
    else:
        print(f"  Notion DB: {DATABASE_ID}")
    print(f"  SQLite: {DB_PATH}")
    print(f"  Allowed domains: {', '.join(ALLOWED_DOMAINS) or 'ALL (verification required)'}")
    if not ADMIN_KEY:
        print("  WARNING: PORTAL_ADMIN_KEY not set — admin endpoints disabled")
    else:
        print(f"  Admin key: {ADMIN_KEY[:4]}{'*' * (len(ADMIN_KEY) - 4)}")
    if os.getenv("SLACK_BOT_TOKEN"):
        print("  Slack bot: enabled")
    port = int(os.environ.get("PORT", "3000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
