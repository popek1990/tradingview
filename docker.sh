#!/bin/bash

# Quick update & rebuild script for TradingView-Webhook-Bot
# Usage: ./docker.sh

echo "Stopping containers..."
docker compose down

echo "Pulling latest changes from GitHub..."
git pull origin main

echo "Rebuilding images and starting (detached)..."
docker compose up -d --build

echo "Cleaning up unused images..."
docker image prune -f

echo "Done! TradingView-Webhook-Bot has been updated and started."
echo "Check logs with: docker compose logs -f"
