#!/bin/bash

# make sure to activate the virtual environment
source venv/bin/activate

echo "🏈 Pick6 Development Data Reset"
echo "=============================="
echo ""
echo "This will:"
echo "  1. Drop all league/user tables (preserves schools & games)"
echo "  2. Recreate with new draft-ready schema"
echo "  3. Load test users and leagues"
echo ""
echo "Test accounts (password: test123):"
echo "  📧 mike@test.com → Mike"
echo "  📧 sarah@test.com → Sarah"  
echo "  📧 alex@test.com → Alex"
echo "  📧 jordan@test.com → Jordan"
echo "  📧 test@test.com → Test User"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️  Resetting league data..."
    echo "yes" | python3 scripts/reset_league_data.py
    
    echo ""
    echo "📦 Loading mock data..."
    python3 scripts/load_mock_data.py
    
    echo ""
    echo "🎉 Ready for development!"
    echo "   Frontend can now connect and test the full flow"
else
    echo "❌ Cancelled"
fi
