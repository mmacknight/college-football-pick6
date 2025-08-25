#!/bin/bash

echo "🛑 Stopping Pick6 Backend..."
echo ""

echo "📦 Stopping Docker containers..."
docker-compose down

echo "✅ Backend stopped!"
echo ""
echo "💡 To start again: ./start-local.sh"
