#!/bin/bash

# Prosty skrypt do aktualizacji i przebudowy TradingView-Webhook-Bot
# Użycie: ./docker.sh

echo "🛑 Zatrzymywanie kontenerów..."
docker compose down

echo "📥 Pobieranie najnowszych zmian z GitHub..."
git pull origin main

echo "🏗️ Przebudowa obrazów i uruchamianie (detached)..."
docker compose up -d --build

echo "🧹 Usuwanie nieużywanych obrazów (cleanup)..."
docker image prune -f

echo "✅ Gotowe! TradingView-Webhook-Bot został zaktualizowany i uruchomiony."
echo "Możesz sprawdzić logi komendą: docker compose logs -f"
