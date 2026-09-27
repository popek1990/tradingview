#!/bin/bash
# Quick update & rebuild script for TradingView-Webhook-Bot
# Usage: ./docker.sh   (run as root from the project directory)
#
# Order matters: the old containers keep receiving alerts while the new images
# build — TradingView does not retry a webhook that finds the server down.
set -euo pipefail
cd "$(dirname "$0")"

echo "Pulling latest changes from GitHub..."
git pull --ff-only origin main

echo "Backing up aliases (data volume)..."
mkdir -p backups
if docker compose ps --status running --services 2>/dev/null | grep -qx dashboard; then
    docker compose cp dashboard:/usr/src/app/data/aliases.json \
        "backups/aliases-$(date +%Y%m%d-%H%M%S).json" \
        || echo "WARNING: alias backup failed — continuing"
fi

# Both containers run as appuser (UID 1000): the webhook reads .env, the
# dashboard writes it. Nobody else on the host needs access to the secrets.
echo "Securing .env..."
touch .env
chown 1000:1000 .env
chmod 600 .env

echo "Building images (old containers still running)..."
docker compose build

echo "Starting new containers..."
docker compose up -d

echo "Cleaning up unused images..."
docker image prune -f

echo "Done! TradingView-Webhook-Bot has been updated and started."
echo "Check logs with: docker compose logs -f"
