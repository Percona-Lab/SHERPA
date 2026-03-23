# SHERPA

**Stakeholder Hub for Enhancement Request Prioritization & Action**

A discovery-informed product intelligence platform that aggregates evidence from 14+ data sources, scores demand signals with transparent dual metrics (Business Impact + User Value), and actively prevents opinion-based prioritization. Built on [Gilad](https://itamargilad.com/discovery-problems)/[Cagan](https://www.svpg.com/) principles: signals are framed as problems, not features; scoring is never opaque; and anti-SCORE safeguards flag sparse or single-source evidence before it becomes a "must-have."

> 100% vibe coded with [Claude](https://claude.ai)

## Architecture

```
Browser ──► Flask (port 3000) ──► Notion API
                │
                ├── portal.db (SQLite: voters, votes, comments)
                ├── SMTP (verification emails)
                ├── demand/ (Demand Signal Engine)
                │     ├── Notion DBs (signals + evidence)
                │     ├── Git-backed signal store
                │     ├── LLM semantic matching (optional)
                │     └── Slack webhook notifications (optional)
                └── bot/ (Slack Bot)
                      ├── /sherpa slash commands
                      ├── Enterprise search
                      ├── Channel notifications
                      └── APScheduler (digest + anomaly scan)
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Required
export NOTION_API_KEY="ntn_xxxxxxxxx"

# Optional: SMTP for email verification (without it, codes print to console)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="sherpa@percona.com"
export SMTP_PASS="app-password-here"
export SMTP_FROM="sherpa@percona.com"

# Required: admin key for /admin panel
export PORTAL_ADMIN_KEY="your-secret-admin-key"

# Optional: Demand Signal Engine
export SHERPA_GIT_REPO_PATH="/path/to/sherpa-signals-repo"    # Git-backed signal store
export SHERPA_SLACK_WEBHOOK_URL="https://hooks.slack.com/..."  # Slack webhook notifications
export SHERPA_LLM_ENDPOINT="https://..."                       # LLM for semantic matching

# Optional: Slack Bot
export SLACK_BOT_TOKEN="xoxb-..."           # Bot token from Slack app
export SLACK_SIGNING_SECRET="..."           # Signing secret from Slack app
export SLACK_CHANNEL_ID="C0123456789"       # Channel for digests and alerts

python server.py
# → http://localhost:3000       (SHERPA portal)
# → http://localhost:3000/admin (admin panel)
# → /slack/events              (Slack bot events endpoint)
# → /slack/commands            (Slack slash commands endpoint)
```

### Dev mode (no SMTP)
Without SMTP env vars, verification codes print to the terminal. Perfect for local testing.

### Graceful Degradation
Every capability is independently optional:
- **No Notion key** → portal won't load features but won't crash
- **No SMTP** → verification codes print to console
- **No Slack tokens** → bot and proactive monitoring disabled
- **No Git repo path** → signals stored locally in `sherpa_data/`
- **No LLM endpoint** → matching falls back to keyword overlap

## Features

### Voting Portal
- **Email verified** — one vote per email address
- **Importance levels** — Nice to have / Important / Critical
- Importance breakdown shown as a colored bar on each card

### Comments
- Verified users can comment on any feature
- Display names shown, emails masked for privacy

### Admin Panel (`/admin`)
- Authenticate with admin key
- View all voters, votes, and comments
- **Remove spam votes** individually
- **Remove comments**
- **Block voters** — removes all their votes and hides comments

### Demand Signal Engine (Discovery-Informed)
- **Problem-level framing** — LLM extracts the underlying need, not just the feature request
- **Dual scoring** — Business Impact (MRR, deal blockers, churn) + User Value (community, surveys, calls)
- **Source diversity tracking** — signals corroborated across source types rank higher
- **Confidence levels** — Strong / Moderate / Weak based on evidence quality and breadth
- **Anti-SCORE warnings** — flags Sparse Evidence, Single Source, Stale Data, No Customer/Community Data
- **Transparent scoring** — every signal shows *why* it ranks where it does, not just a number
- 14+ data sources: Salesforce, TAM/SDM/SE notes, Update.AI, GitHub, Forums, Surveys, ServiceNow, and more
- LLM-powered problem-level matching (with keyword fallback)
- Git-backed canonical signal store + two-way Notion sync

### Slack Bot (`/sherpa`)
- `/sherpa search [query]` — Search demand signals
- `/sherpa log "[feedback]"` — Log evidence manually
- `/sherpa top [product]` — Top 10 signals by demand score
- `/sherpa signal [id]` — Signal details with score breakdown
- `/sherpa digest` — Trigger weekly digest on demand
- `@sherpa` mentions in channels

### Proactive Monitoring
- **Weekly digest** — Top signals, new evidence, and trends posted to Slack every Monday at 9 AM
- **Anomaly scan** — Detects score spikes, evidence surges, and new high-score signals every 4 hours

## File Structure

```
SHERPA/
├── server.py              # Flask backend + Slack event routes + APScheduler
├── portal.db              # Auto-created SQLite database
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html         # Main voting portal
│   └── admin.html         # Admin panel
├── demand/                # Demand Signal Engine (discovery-informed)
│   ├── __init__.py
│   ├── models.py          # DemandSignal (problem-level), CustomerEvidence
│   ├── ingestion.py       # Extract → Classify → Match → Store pipeline
│   ├── matching.py        # LLM problem-level match + keyword fallback
│   ├── scoring.py         # Dual scoring: Business Impact + User Value
│   ├── git_sync.py        # Git-backed canonical store
│   ├── notion_sync.py     # Notion database read/write sync
│   └── slack_notify.py    # Slack webhook notifications
└── bot/                   # Slack Bot
    ├── __init__.py
    ├── handlers.py        # /sherpa slash commands + event handlers
    ├── search.py          # Enterprise signal search
    └── notifications.py   # Digest + anomaly alert formatting
```

## API Reference

### Auth
| Endpoint | Method | Body |
|---|---|---|
| `/api/auth/request-code` | POST | `{ "email": "...", "display_name": "..." }` |
| `/api/auth/verify` | POST | `{ "email": "...", "code": "123456" }` |
| `/api/auth/check` | GET | Header: `X-Voter-Token: {voter_id}` |

### Features & Voting
| Endpoint | Method | Description |
|---|---|---|
| `/api/features` | GET | List published features with vote counts |
| `/api/vote` | POST | `{ "feature_id": "...", "importance": "critical", "action": "upvote" }` |
| `/api/comments/{feature_id}` | GET | Get comments for a feature |
| `/api/comments` | POST | `{ "feature_id": "...", "body": "..." }` |

### Admin (requires `X-Admin-Key` header)
| Endpoint | Method | Description |
|---|---|---|
| `/api/admin/voters` | GET | List all voters with stats |
| `/api/admin/votes` | GET | List all votes |
| `/api/admin/comments` | GET | List all comments |
| `/api/admin/vote/{id}` | DELETE | Remove a vote |
| `/api/admin/comment/{id}` | DELETE | Hide a comment |
| `/api/admin/voter/{id}/block` | POST | `{ "block": true }` — block/unblock voter |

### Demand Signal Engine
| Endpoint | Method | Description |
|---|---|---|
| `/api/sherpa/ingest` | POST | Ingest evidence from external sources (Slack, Jira, forums) |
| `/api/sherpa/signals` | GET | List all demand signals with scores |
| `/api/sherpa/signals/{id}` | GET | Get a single signal with all evidence |
| `/api/sherpa/notion-status` | GET | Check Notion sync configuration and status |

Votes and comments are automatically ingested as customer evidence and synced to two Notion databases (Demand Signals + Customer Evidence). External sources can POST evidence to `/api/sherpa/ingest`. Without `SHERPA_GIT_REPO_PATH`, signals are stored locally in `sherpa_data/signals/`.

### Slack Bot
| Endpoint | Method | Description |
|---|---|---|
| `/slack/events` | POST | Slack Events API (bot mentions, messages) |
| `/slack/commands` | POST | Slack slash command handler (`/sherpa`) |
