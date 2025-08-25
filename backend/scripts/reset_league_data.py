#!/usr/bin/env python3
"""
Reset League Data Script
Drops all league-related tables and recreates with new schema
Preserves schools and games data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'shared'))

from database import get_db_session
from sqlalchemy import text

def reset_league_tables():
    """Drop and recreate league tables with new schema"""
    db = get_db_session()
    
    try:
        print("🗑️  Dropping existing league tables...")
        
        # Drop tables in correct order (foreign keys)
        drop_statements = [
            "DROP TABLE IF EXISTS league_team_school_assignments CASCADE;",
            "DROP TABLE IF EXISTS league_drafts CASCADE;",
            "DROP TABLE IF EXISTS league_teams CASCADE;",
            "DROP TABLE IF EXISTS leagues CASCADE;",
            "DROP TABLE IF EXISTS users CASCADE;"
        ]
        
        for statement in drop_statements:
            db.execute(text(statement))
        
        print("✅ Dropped old tables")
        
        print("🏗️  Creating new league schema...")
        
        # Create users table
        users_sql = """
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create leagues table with new statuses
        leagues_sql = """
        CREATE TABLE leagues (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            season INTEGER NOT NULL,
            join_code VARCHAR(8) UNIQUE NOT NULL,
            created_by UUID REFERENCES users(id),
            status VARCHAR(20) DEFAULT 'pre_draft', -- pre_draft, drafting, active, completed
            max_teams_per_user INTEGER DEFAULT 6,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create league_teams (normalized - composite PK)
        league_teams_sql = """
        CREATE TABLE league_teams (
            league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            team_name VARCHAR(100), -- "Mike's Dominators" (optional)
            draft_position INTEGER, -- 1, 2, 3, 4 (draft order within league)
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (league_id, user_id) -- composite key: one team per user per league
        );
        """
        
        # Create league_team_school_assignments (normalized - composite PK)
        assignments_sql = """
        CREATE TABLE league_team_school_assignments (
            league_id UUID,
            user_id UUID,
            school_id INTEGER REFERENCES schools(id),
            draft_round INTEGER, -- 1, 2, 3, 4
            draft_pick_overall INTEGER, -- 1-16 in 4-person league
            drafted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (league_id, user_id, school_id), -- composite key: prevents duplicate picks
            FOREIGN KEY (league_id, user_id) REFERENCES league_teams(league_id, user_id) ON DELETE CASCADE,
            UNIQUE(league_id, school_id), -- each school can only be picked once per league
            UNIQUE(league_id, draft_pick_overall) -- each overall pick number is unique
        );
        """
        
        # Create league_drafts table
        drafts_sql = """
        CREATE TABLE league_drafts (
            league_id UUID PRIMARY KEY REFERENCES leagues(id) ON DELETE CASCADE,
            current_pick_overall INTEGER DEFAULT 1,
            current_league_id UUID,
            current_user_id UUID,
            total_picks INTEGER, -- members * max_teams_per_user
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (current_league_id, current_user_id) REFERENCES league_teams(league_id, user_id)
        );
        """
        
        # Execute table creation
        for sql in [users_sql, leagues_sql, league_teams_sql, assignments_sql, drafts_sql]:
            db.execute(text(sql))
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX idx_league_teams_league ON league_teams(league_id);",
            "CREATE INDEX idx_league_teams_user ON league_teams(user_id);",
            "CREATE INDEX idx_assignments_league ON league_team_school_assignments(league_id);",
            "CREATE INDEX idx_assignments_user ON league_team_school_assignments(user_id);",
            "CREATE INDEX idx_assignments_school ON league_team_school_assignments(school_id);",
            "CREATE INDEX idx_assignments_draft_order ON league_team_school_assignments(league_id, draft_pick_overall);",
        ]
        
        for sql in indexes_sql:
            db.execute(text(sql))
        
        db.commit()
        print("✅ Created new league schema")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🏈 Pick6 League Data Reset")
    print("This will drop all league, user, and team data")
    print("Schools and games will be preserved")
    
    confirm = input("\nAre you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_league_tables()
        print("\n🎉 Reset complete! Ready for new schema.")
    else:
        print("❌ Cancelled")
