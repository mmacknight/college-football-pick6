#!/bin/bash

# Copy Production Database to Dev (both on Neon)
# This script dumps the production Neon database and loads it into dev Neon database

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database URLs - both on Neon
PROD_DB_URL="postgresql://neondb_owner:npg_QFpa0ePGEn2K@ep-holy-bonus-adx50ti1-pooler.c-2.us-east-1.aws.neon.tech/pick6_prod?sslmode=require"
DEV_DB_URL="postgresql://neondb_owner:npg_QFpa0ePGEn2K@ep-late-tree-ad6pyjlo-pooler.c-2.us-east-1.aws.neon.tech/pick6_dev?sslmode=require"

DUMP_FILE="/tmp/prod_db_dump.sql"

echo ""
echo "======================================================================"
echo -e "${BLUE}🚀 COPY PRODUCTION DATABASE TO DEV (Neon → Neon)${NC}"
echo "======================================================================"
echo ""

# Confirm with user (skip if -y flag provided)
echo -e "${YELLOW}⚠️  WARNING: This will:${NC}"
echo "   1. Export the entire production database from Neon"
echo "   2. DROP all tables in your dev Neon database"
echo "   3. Load all production data into dev Neon database"
echo ""
echo -e "${RED}   All existing data in your dev Neon database will be LOST!${NC}"
echo ""

if [[ "$1" != "-y" ]]; then
    read -p "❓ Are you sure you want to continue? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy](es)?$ ]]; then
        echo -e "${RED}❌ Aborted by user${NC}"
        exit 1
    fi
else
    echo "Auto-confirming (use without -y to see prompt)..."
    echo ""
fi

# Step 1: Dump production database
echo "======================================================================"
echo -e "${BLUE}Step 1: Dumping production database...${NC}"
echo "======================================================================"
echo ""

# Use PostgreSQL 17 pg_dump to match production server version
PG_DUMP="/opt/homebrew/opt/postgresql@17/bin/pg_dump"
if [ ! -f "$PG_DUMP" ]; then
    PG_DUMP="pg_dump"  # Fallback to system pg_dump
fi

if $PG_DUMP "$PROD_DB_URL" --no-owner --no-privileges --clean --if-exists -f "$DUMP_FILE"; then
    DUMP_SIZE=$(ls -lh "$DUMP_FILE" | awk '{print $5}')
    echo -e "${GREEN}✅ Production database dumped to $DUMP_FILE${NC}"
    echo -e "📊 Dump file size: $DUMP_SIZE"
else
    echo -e "${RED}❌ Failed to dump production database${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  • Make sure pg_dump is installed (brew install postgresql)"
    echo "  • Check your internet connection"
    echo "  • Verify the production database URL is correct"
    exit 1
fi

# Step 2: Load production data into dev Neon database
# The dump file has --clean --if-exists flags, so it will drop tables automatically
echo ""
echo "======================================================================"
echo -e "${BLUE}Step 2: Loading production data into dev Neon...${NC}"
echo "======================================================================"
echo ""
echo "This may take a minute..."
echo ""

# Use PostgreSQL 17 psql to match server version
PSQL="/opt/homebrew/opt/postgresql@17/bin/psql"
if [ ! -f "$PSQL" ]; then
    PSQL="psql"  # Fallback to system psql
fi

if $PSQL "$DEV_DB_URL" -f "$DUMP_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Production data loaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to load production data${NC}"
    exit 1
fi

# Step 3: Clean up
echo ""
echo "======================================================================"
echo -e "${BLUE}Step 3: Cleaning up...${NC}"
echo "======================================================================"
echo ""

rm -f "$DUMP_FILE"
echo -e "${GREEN}✅ Removed temporary dump file${NC}"

# Step 4: Show summary
echo ""
echo "======================================================================"
echo -e "${GREEN}🎉 SUCCESS!${NC}"
echo "======================================================================"
echo ""
echo "Your dev Neon database now contains all data from production:"
echo "  • All schools/teams"
echo "  • All games and scores"
echo "  • All users (hashed passwords)"
echo "  • All leagues and members"
echo "  • All drafts and team assignments"
echo ""
echo "📝 Next steps:"
echo "  1. Your deployed dev environment will now have production data"
echo ""
echo "  2. Test your dev app with production data"
echo ""
echo "  3. Remember: Changes you make in dev won't affect production!"
echo ""
echo "======================================================================"
echo ""

