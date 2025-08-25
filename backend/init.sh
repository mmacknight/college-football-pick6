#!/bin/bash

echo "🔧 Initializing Pick6 Backend Development Environment..."
echo ""

# Check if we're in the backend directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Must run from backend directory"
    echo "   cd backend && ./init.sh"
    exit 1
fi

# Check if Colima is running
if ! colima status >/dev/null 2>&1; then
    echo "❌ Colima is not running. Start with: colima start"
    exit 1
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check for AWS SAM CLI
if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI is required but not installed"
    echo "   Install with: brew install aws-sam-cli"
    exit 1
fi

echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

echo "🐍 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🐳 Pulling Docker images..."
docker-compose pull

echo ""
echo "✅ Backend development environment initialized!"
echo ""
echo "🚀 Next steps:"
echo "   1. Start backend: ./start-local.sh"
echo "   2. Visit API: http://localhost:3001"
echo "   3. Visit DB UI: http://localhost:8080"
echo ""
echo "🛑 To stop: ./stop-local.sh"
