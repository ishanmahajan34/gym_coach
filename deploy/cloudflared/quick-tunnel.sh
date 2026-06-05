#!/bin/bash
# Expose the app over HTTPS without a domain using Cloudflare Quick Tunnels.
# URL changes every restart — fine for personal testing.
# For a stable URL you need a domain + named tunnel (see Cloudflare docs).

set -e

if ! command -v cloudflared &>/dev/null; then
    echo "Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
        -o /usr/local/bin/cloudflared
    chmod +x /usr/local/bin/cloudflared
fi

echo "Starting quick tunnel -> http://localhost:8000"
echo "Your HTTPS URL will appear below (changes on restart):"
cloudflared tunnel --url http://localhost:8000
