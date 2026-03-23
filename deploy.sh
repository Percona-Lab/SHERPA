#!/usr/bin/env bash
set -euo pipefail

# SHERPA deploy script
# Usage: ./deploy.sh staging   — pull latest, restart staging
#        ./deploy.sh prod      — pull latest, restart prod

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO_DIR/venv"

ENV="${1:-}"
if [[ "$ENV" != "staging" && "$ENV" != "prod" ]]; then
    echo "Usage: $0 {staging|prod}"
    exit 1
fi

SERVICE="sherpa-${ENV}"

echo "=== Deploying SHERPA ($ENV) ==="
echo "Repo:    $REPO_DIR"
echo "Service: $SERVICE"
echo ""

# 1. Pull latest code
echo "--- git pull ---"
cd "$REPO_DIR"
git fetch origin
git reset --hard origin/main
echo ""

# 2. Install/update dependencies
echo "--- pip install ---"
"$VENV/bin/pip" install -q -r requirements.txt
echo ""

# 3. Ensure data directory exists
DATA_DIR="/home/dennis.kittrell/sherpa-${ENV}"
mkdir -p "$DATA_DIR"
echo "Data dir: $DATA_DIR"

# 4. Restart the systemd service
echo "--- restarting $SERVICE ---"
sudo systemctl restart "$SERVICE"
sleep 2

# 5. Verify
if systemctl is-active --quiet "$SERVICE"; then
    echo ""
    echo "OK: $SERVICE is running"
    systemctl status "$SERVICE" --no-pager -l | head -15
else
    echo ""
    echo "FAIL: $SERVICE did not start"
    journalctl -u "$SERVICE" --no-pager -n 20
    exit 1
fi
