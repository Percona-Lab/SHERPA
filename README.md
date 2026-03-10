# SHERPA

**Stakeholder Hub for Enhancement Request Prioritization & Action**

A feature voting portal backed by Notion, with email-verified voting. Percona employees vote on features based on customer and market needs, helping align product priorities with real demand.

> 100% vibe coded with [Claude](https://claude.ai)

## Architecture

```
Browser ──► Flask (port 3000) ──► Notion API
                │
                ├── portal.db (SQLite: voters, votes, comments)
                ├── SMTP (verification emails)
                └── pdaa/ (Demand Signal Agent)
                      ├── Notion DBs (signals + evidence)
                      ├── Git-backed signal store
                      ├── LLM semantic matching (optional)
                      └── Slack notifications (optional)
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

# Optional: PDAA Demand Signal Agent
export PDAA_GIT_REPO_PATH="/path/to/pdaa-signals-repo"    # Git-backed signal store
export PDAA_SLACK_WEBHOOK_URL="https://hooks.slack.com/..." # Slack notifications
export PDAA_LLM_ENDPOINT="https://..."                      # LLM for semantic matching

python server.py
# → http://localhost:3000       (SHERPA portal)
# → http://localhost:3000/admin (admin panel)
```

### Dev mode (no SMTP)
Without SMTP env vars, verification codes print to the terminal. Perfect for local testing.

## Features

### Voting
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

## File Structure

```
SHERPA/
├── server.py           # Flask backend
├── portal.db           # Auto-created SQLite database
├── static/
│   ├── index.html      # Main portal
│   └── admin.html      # Admin panel
└── pdaa/               # Demand Signal Agent sub-package
    ├── __init__.py
    ├── models.py       # DemandSignal, CustomerEvidence dataclasses
    ├── ingestion.py    # Extract → Classify → Match → Store pipeline
    ├── matching.py     # LLM semantic match + keyword fallback
    ├── scoring.py      # Weighted demand score formula
    ├── git_sync.py     # Git-backed canonical store
    ├── notion_sync.py  # Notion database read/write sync
    ├── slack_notify.py # Slack Block Kit notifications
    └── sherpa_connector.py  # Vote/comment → evidence conversion
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

### PDAA Demand Signal Agent
| Endpoint | Method | Description |
|---|---|---|
| `/api/pdaa/ingest` | POST | Ingest evidence from external sources (Slack, Jira, forums) |
| `/api/pdaa/signals` | GET | List all demand signals with scores |
| `/api/pdaa/signals/{id}` | GET | Get a single signal with all evidence |
| `/api/pdaa/notion-status` | GET | Check Notion sync configuration and status |

SHERPA votes and comments are automatically ingested into PDAA and synced to two Notion databases (Demand Signals + Customer Evidence). External sources can POST evidence to `/api/pdaa/ingest`. Without `PDAA_GIT_REPO_PATH`, signals are also stored locally in `pdaa_data/signals/`.

## Roadmap

Planned improvements, roughly in priority order. Items marked with **n8n** leverage the existing n8n automation infrastructure.

### Phase 1 — Notifications & Visibility
- [ ] **n8n** Slack alerts on votes/comments — webhook from SHERPA posts to a `#product-feedback` channel when someone votes or comments
- [ ] **n8n** Weekly digest — scheduled workflow aggregates top-voted features, new comments, and trending items → posts summary to Slack or email
- [ ] **n8n** Vote threshold alerts — notify product owners via Slack DM when a feature crosses a configurable vote threshold

### Phase 2 — Feedback Loop
- [ ] **n8n** Status change notifications — poll Notion for status updates (→ In Progress, → Shipped) and notify voters who cared about that feature
- [ ] **n8n** Cache invalidation webhook — when Notion data changes, trigger SHERPA to refresh so the portal stays current
- [ ] Add a `/api/webhook` endpoint in SHERPA for n8n to call (vote events, cache busting)

### Phase 3 — Cross-system Integration
- [ ] **n8n** Jira ticket creation — auto-create Jira epic/story when a feature hits enough traction (votes + comments), linked back to the Notion page
- [ ] **n8n** CRM enrichment — pull customer context (ARR, segment) from Salesforce to give PMs a revenue-weighted demand view

### Phase 4 — Analytics & Observability
- [ ] **n8n** Activity logging to Elastic — ship SHERPA events (votes, comments, logins) to the existing Elastic stack for dashboards and trend analysis
- [ ] Engagement metrics — track unique visitors, vote-to-visit ratio, comment activity over time
