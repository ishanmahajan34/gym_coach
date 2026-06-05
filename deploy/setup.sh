#!/bin/bash
# Run this once on a fresh Oracle Cloud Ubuntu 22.04 ARM instance.
# Usage: bash setup.sh
set -e

APP_DIR="/opt/gym_coach"
SERVICE_USER="coach"

echo "=== Installing system deps ==="
sudo apt-get update -q
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev git curl

echo "=== Creating app user ==="
sudo useradd -r -s /bin/false -d "$APP_DIR" "$SERVICE_USER" 2>/dev/null || echo "User already exists"

echo "=== Setting up app directory ==="
sudo mkdir -p "$APP_DIR/data"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

echo "=== Copying app files ==="
# Run from your local machine with scp, or git clone here.
# This script assumes you've already placed the code at $APP_DIR.

echo "=== Creating virtualenv ==="
sudo -u "$SERVICE_USER" python3.11 -m venv "$APP_DIR/.venv"
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip -q
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install -e "$APP_DIR" -q

echo "=== Installing systemd service ==="
sudo cp "$(dirname "$0")/coach.service" /etc/systemd/system/coach.service
sudo systemctl daemon-reload
sudo systemctl enable coach

echo "=== Opening port 8000 in iptables ==="
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save 2>/dev/null || true

echo ""
echo "Done. Next steps:"
echo "  1. Make sure /opt/gym_coach/.env is in place (see .env.example)"
echo "  2. sudo systemctl start coach"
echo "  3. sudo systemctl status coach"
echo "  4. Open http://<your-oracle-ip>:8000"
