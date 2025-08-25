#!/bin/bash

echo "🚀 Starting Pick6 Backend..."
echo ""

# Check if we're in the backend directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Must run from backend directory"
    echo "   cd backend && ./start-local.sh"
    exit 1
fi

# Check if Colima is running
if ! colima status >/dev/null 2>&1; then
    echo "❌ Colima is not running. Start with: colima start"
    exit 1
fi

echo "📦 Starting PostgreSQL with Docker..."
docker-compose up -d

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL to be healthy
while ! docker exec pick6-postgres pg_isready -U pick6admin -d pick6db >/dev/null 2>&1; do
    echo "   Still waiting for PostgreSQL..."
    sleep 2
done

echo "✅ PostgreSQL is ready!"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Python virtual environment not found!"
    echo "   Run: ./init.sh first"
    exit 1
fi

echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

echo ""
echo "🚀 Starting AWS SAM local API..."
echo "   API will be available at: http://localhost:3001"
echo "   Database UI at: http://localhost:8080"
echo ""
echo "📊 Database credentials:"
echo "   Host: localhost:5432"
echo "   Database: pick6db"
echo "   Username: pick6admin" 
echo "   Password: pick6password"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if --dev flag is passed
if [[ "$1" == "--dev" ]]; then
    echo "🐍 Starting unified development server..."
    echo "   API Server: http://localhost:3001"
    echo "   Includes WebSocket support (if flask-socketio installed)"
    echo ""
    
    if [[ "$2" == "--gunicorn" ]]; then
        echo "⚡ Using Gunicorn for better performance..."
        python3 dev_server.py --gunicorn
    else
        echo "💡 Tip: For multiple browsers, use: ./start-local.sh --dev --gunicorn"
        python3 dev_server.py
    fi
else
    # Set Docker host for SAM CLI to work with Colima
    export DOCKER_HOST="unix://$HOME/.colima/docker.sock"

    echo "🔨 Building SAM application..."
    sam build

    echo ""
    echo "🚀 Starting SAM local API server..."
    # Start SAM local API
    sam local start-api --port 3001 --env-vars local-env.json
fi
