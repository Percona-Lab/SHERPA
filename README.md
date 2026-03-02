# SHERPA

**Stakeholder Hub for Enhancement Request Prioritization & Action**

A feature voting portal backed by Notion, with email-verified voting. Percona employees vote on features based on customer and market needs, helping align product priorities with real demand.

> 100% vibe coded with [Claude](https://claude.ai)

## Architecture

```
Browser ──► Flask (port 3000) ──► Notion API
                │
                └── portal.db (SQLite: voters, votes, comments)
                │
                └── SMTP (verification emails)
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests

# Required
export NOTION_API_KEY="ntn_xxxxxxxxx"

# Optional: SMTP for email verification (without it, codes print to console)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="sherpa@percona.com"
export SMTP_PASS="app-password-here"
export SMTP_FROM="sherpa@percona.com"

# Optional: custom admin key (default: changeme-admin-2025)
export PORTAL_ADMIN_KEY="your-secret-admin-key"

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
└── static/
    ├── index.html      # Main portal
    └── admin.html      # Admin panel
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
