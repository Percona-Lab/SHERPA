#!/usr/bin/env bash
set -euo pipefail

# SHERPA deploy script — isolated environments
#
# Layout:
#   ~/sherpa-prod/code/     separate git clone
#   ~/sherpa-prod/venv/     separate virtualenv
#   ~/sherpa-prod/data/     portal.db + cache
#   ~/sherpa-prod/env.conf  environment overrides
#
#   ~/sherpa-staging/...    same structure
#
# Usage:
#   ./deploy.sh staging          # deploy latest main to staging (:3001)
#   ./deploy.sh prod             # deploy latest main to prod (:3000)
#   ./deploy.sh prod v1.2.3      # deploy specific tag to prod
#   ./deploy.sh setup            # one-time: create both environments

REPO_URL="https://github.com/Percona-Lab/SHERPA.git"
HOME_DIR="/home/dennis.kittrell"

ENV="${1:-}"
REF="${2:-origin/main}"

# ─── One-time setup ───
if [[ "$ENV" == "setup" ]]; then
    echo "=== Setting up SHERPA environments ==="

    for e in prod staging; do
        BASE="$HOME_DIR/sherpa-${e}"
        echo ""
        echo "--- Setting up $e at $BASE ---"

        mkdir -p "$BASE/data"

        # Clone if not present
        if [[ ! -d "$BASE/code/.git" ]]; then
            git clone "$REPO_URL" "$BASE/code"
        fi

        # Create venv if not present
        if [[ ! -d "$BASE/venv" ]]; then
            python3 -m venv "$BASE/venv"
        fi

        "$BASE/venv/bin/pip" install -q -r "$BASE/code/requirements.txt"

        # Create env.conf if not present
        if [[ ! -f "$BASE/env.conf" ]]; then
            if [[ "$e" == "prod" ]]; then PORT=3000; else PORT=3001; fi
            cat > "$BASE/env.conf" << ENVEOF
PORT=$PORT
FLASK_DEBUG=0
SHERPA_DATA_DIR=$BASE/data
ENVEOF
            echo "Created $BASE/env.conf"
        fi
    done

    echo ""
    echo "=== Setup complete ==="
    echo "Next steps:"
    echo "  sudo cp ~/sherpa-prod/code/deploy/sherpa-prod.service /etc/systemd/system/"
    echo "  sudo cp ~/sherpa-staging/code/deploy/sherpa-staging.service /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable sherpa-prod sherpa-staging"
    echo "  ./deploy.sh staging"
    echo "  ./deploy.sh prod"
    exit 0
fi

# ─── Deploy to environment ───
if [[ "$ENV" != "staging" && "$ENV" != "prod" ]]; then
    echo "Usage: $0 {staging|prod|setup} [git-ref]"
    echo ""
    echo "  $0 staging          Deploy latest main to staging"
    echo "  $0 prod             Deploy latest main to prod"
    echo "  $0 prod v1.2.3      Deploy specific tag to prod"
    echo "  $0 setup            One-time environment setup"
    exit 1
fi

SERVICE="sherpa-${ENV}"
BASE="$HOME_DIR/sherpa-${ENV}"
CODE="$BASE/code"
VENV="$BASE/venv"

if [[ ! -d "$CODE/.git" ]]; then
    echo "ERROR: $CODE does not exist. Run './deploy.sh setup' first."
    exit 1
fi

echo "=== Deploying SHERPA ($ENV) ==="
echo "Code:    $CODE"
echo "Ref:     $REF"
echo "Service: $SERVICE"
echo ""

# 1. Pull latest code into this environment's clone
echo "--- git fetch + checkout ---"
cd "$CODE"
git fetch origin
git reset --hard "$REF"
echo "Now at: $(git log --oneline -1)"
echo ""

# 2. Install/update dependencies
echo "--- pip install ---"
"$VENV/bin/pip" install -q -r requirements.txt
echo ""

# 3. Ensure data directory exists
mkdir -p "$BASE/data"

# 4. Clean up stale gunicorn control socket and restart
rm -f "$CODE/gunicorn.ctl"
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
