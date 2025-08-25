#!/usr/bin/env python3
"""
Load Mock Data Script
Creates test users, leagues, and teams for development testing
All passwords are 'test123' for easy login
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'shared'))

from database import get_db_session
from sqlalchemy import text
import bcrypt
import json
import random
import string

def generate_join_code():
    """Generate 8-character join code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def load_mock_data():
    """Load mock users, leagues, and teams"""
    db = get_db_session()
    
    try:
        print("👥 Creating test users...")
        
        # Test users - all with password 'test123'
        password_hash = hash_password('test123')
        
        users = [
            {'email': 'mike@test.com', 'display_name': 'Mike', 'team_name': "Mike's Dominators"},
            {'email': 'sarah@test.com', 'display_name': 'Sarah', 'team_name': "Sarah's Squad"},
            {'email': 'alex@test.com', 'display_name': 'Alex', 'team_name': "Alex's Aces"},
            {'email': 'jordan@test.com', 'display_name': 'Jordan', 'team_name': "Jordan's Juggernauts"},
            {'email': 'test@test.com', 'display_name': 'Test User', 'team_name': "Test Team"}
        ]
        
        user_ids = {}
        
        for user in users:
            result = db.execute(text("""
                INSERT INTO users (email, password_hash, display_name)
                VALUES (:email, :password_hash, :display_name)
                RETURNING id
            """), {
                'email': user['email'],
                'password_hash': password_hash,
                'display_name': user['display_name']
            })
            user_id = result.fetchone()[0]
            user_ids[user['display_name']] = {
                'id': user_id,
                'team_name': user['team_name']
            }
        
        print(f"✅ Created {len(users)} test users")
        
        print("🏈 Creating test leagues...")
        
        # Test leagues with different states
        leagues = [
            {
                'name': 'Pre-Draft Test League',
                'season': 2024,
                'created_by': user_ids['Mike']['id'],
                'status': 'pre_draft'  # No picks yet, can still edit settings
            },
            {
                'name': 'Mid-Draft League',
                'season': 2024,
                'created_by': user_ids['Sarah']['id'],
                'status': 'drafting'  # Partially drafted
            },
            {
                'name': 'Active Season League',
                'season': 2024,
                'created_by': user_ids['Alex']['id'],
                'status': 'active'  # Fully drafted, season in progress
            }
        ]
        
        league_ids = {}
        
        for league in leagues:
            join_code = generate_join_code()
            result = db.execute(text("""
                INSERT INTO leagues (name, season, join_code, created_by, status)
                VALUES (:name, :season, :join_code, :created_by, :status)
                RETURNING id
            """), {
                'name': league['name'],
                'season': league['season'],
                'join_code': join_code,
                'created_by': league['created_by'],
                'status': league['status']
            })
            league_id = result.fetchone()[0]
            league_ids[league['name']] = {
                'id': league_id,
                'join_code': join_code,
                'status': league['status']
            }
        
        print(f"✅ Created {len(leagues)} test leagues")
        
        print("🏆 Setting up league memberships and draft states...")
        
        # Common members for all leagues
        all_members = ['Mike', 'Sarah', 'Alex', 'Jordan']
        
        # 1. PRE-DRAFT LEAGUE - Members joined but no draft started
        print("  Setting up Pre-Draft League...")
        pre_draft_id = league_ids['Pre-Draft Test League']['id']
        
        for i, member in enumerate(all_members):
            db.execute(text("""
                INSERT INTO league_teams (league_id, user_id, team_name, draft_position)
                VALUES (:league_id, :user_id, :team_name, :draft_position)
            """), {
                'league_id': pre_draft_id,
                'user_id': user_ids[member]['id'],
                'team_name': user_ids[member]['team_name'],
                'draft_position': None  # No draft positions assigned yet
            })
        print("    ✅ Pre-draft league: 4 members, no picks")
        
        # 2. MID-DRAFT LEAGUE - Draft started, some picks made
        print("  Setting up Mid-Draft League...")
        mid_draft_id = league_ids['Mid-Draft League']['id']
        
        for i, member in enumerate(all_members):
            db.execute(text("""
                INSERT INTO league_teams (league_id, user_id, team_name, draft_position)
                VALUES (:league_id, :user_id, :team_name, :draft_position)
            """), {
                'league_id': mid_draft_id,
                'user_id': user_ids[member]['id'],
                'team_name': user_ids[member]['team_name'],
                'draft_position': i + 1  # 1, 2, 3, 4
            })
        
        # Create draft record for mid-draft league (currently on pick 7)
        db.execute(text("""
            INSERT INTO league_drafts (league_id, current_pick_overall, total_picks, started_at, current_league_id, current_user_id)
            VALUES (:league_id, 7, 24, NOW() - INTERVAL '1 hour', :current_league_id, :current_user_id)
        """), {
            'league_id': mid_draft_id,
            'current_league_id': mid_draft_id,
            'current_user_id': user_ids['Alex']['id']  # Alex's turn (pick 7)
        })
        
        # Add partial picks to mid-draft league (first 6 picks)
        mid_draft_picks = [
            # Round 1: Snake order 1,2,3,4
            {'user': 'Mike', 'school': 'Alabama', 'round': 1, 'overall': 1},
            {'user': 'Sarah', 'school': 'Georgia', 'round': 1, 'overall': 2},
            {'user': 'Alex', 'school': 'Texas', 'round': 1, 'overall': 3},
            {'user': 'Jordan', 'school': 'Miami', 'round': 1, 'overall': 4},
            # Round 2: Reverse order 4,3 (snake draft)
            {'user': 'Jordan', 'school': 'LSU', 'round': 2, 'overall': 5},
            {'user': 'Alex', 'school': 'Oregon', 'round': 2, 'overall': 6},
            # Pick 7 is Alex's turn again (current state)
        ]
        
        for pick in mid_draft_picks:
            school_result = db.execute(text("""
                SELECT id FROM schools WHERE name = :name LIMIT 1
            """), {'name': pick['school']})
            school_row = school_result.fetchone()
            
            if school_row:
                db.execute(text("""
                    INSERT INTO league_team_school_assignments 
                    (league_id, user_id, school_id, draft_round, draft_pick_overall)
                    VALUES (:league_id, :user_id, :school_id, :draft_round, :draft_pick_overall)
                """), {
                    'league_id': mid_draft_id,
                    'user_id': user_ids[pick['user']]['id'],
                    'school_id': school_row[0],
                    'draft_round': pick['round'],
                    'draft_pick_overall': pick['overall']
                })
                print(f"    Pick {pick['overall']}: {pick['user']} → {pick['school']}")
        
        print("    ✅ Mid-draft league: 6/16 picks made, Alex's turn")
        
        # 3. ACTIVE LEAGUE - Fully drafted, all picks complete
        print("  Setting up Active League...")
        active_id = league_ids['Active Season League']['id']
        
        for i, member in enumerate(all_members):
            db.execute(text("""
                INSERT INTO league_teams (league_id, user_id, team_name, draft_position)
                VALUES (:league_id, :user_id, :team_name, :draft_position)
            """), {
                'league_id': active_id,
                'user_id': user_ids[member]['id'],
                'team_name': user_ids[member]['team_name'],
                'draft_position': i + 1  # 1, 2, 3, 4
            })
        
        # Create completed draft record
        db.execute(text("""
            INSERT INTO league_drafts (league_id, current_pick_overall, total_picks, started_at, completed_at, current_league_id, current_user_id)
            VALUES (:league_id, 24, 24, NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days', :current_league_id, NULL)
        """), {
            'league_id': active_id,
            'current_league_id': active_id
        })
        
        # Add complete draft picks to active league (all 24 picks - 6 teams per player)
        active_league_picks = [
            # Round 1: 1,2,3,4
            {'user': 'Mike', 'school': 'Michigan', 'round': 1, 'overall': 1},
            {'user': 'Sarah', 'school': 'Ohio State', 'round': 1, 'overall': 2},
            {'user': 'Alex', 'school': 'USC', 'round': 1, 'overall': 3},
            {'user': 'Jordan', 'school': 'Tennessee', 'round': 1, 'overall': 4},
            # Round 2: 4,3,2,1 (snake)
            {'user': 'Jordan', 'school': 'Florida', 'round': 2, 'overall': 5},
            {'user': 'Alex', 'school': 'Washington', 'round': 2, 'overall': 6},
            {'user': 'Sarah', 'school': 'Penn State', 'round': 2, 'overall': 7},
            {'user': 'Mike', 'school': 'Wisconsin', 'round': 2, 'overall': 8},
            # Round 3: 1,2,3,4
            {'user': 'Mike', 'school': 'Notre Dame', 'round': 3, 'overall': 9},
            {'user': 'Sarah', 'school': 'Clemson', 'round': 3, 'overall': 10},
            {'user': 'Alex', 'school': 'Oklahoma', 'round': 3, 'overall': 11},
            {'user': 'Jordan', 'school': 'Auburn', 'round': 3, 'overall': 12},
            # Round 4: 4,3,2,1 (snake)
            {'user': 'Jordan', 'school': 'Iowa', 'round': 4, 'overall': 13},
            {'user': 'Alex', 'school': 'Utah', 'round': 4, 'overall': 14},
            {'user': 'Sarah', 'school': 'Mississippi State', 'round': 4, 'overall': 15},
            {'user': 'Mike', 'school': 'Kansas State', 'round': 4, 'overall': 16},
            # Round 5: 1,2,3,4
            {'user': 'Mike', 'school': 'Virginia Tech', 'round': 5, 'overall': 17},
            {'user': 'Sarah', 'school': 'North Carolina', 'round': 5, 'overall': 18},
            {'user': 'Alex', 'school': 'Arizona State', 'round': 5, 'overall': 19},
            {'user': 'Jordan', 'school': 'Kentucky', 'round': 5, 'overall': 20},
            # Round 6: 4,3,2,1 (snake)
            {'user': 'Jordan', 'school': 'West Virginia', 'round': 6, 'overall': 21},
            {'user': 'Alex', 'school': 'Colorado', 'round': 6, 'overall': 22},
            {'user': 'Sarah', 'school': 'Boston College', 'round': 6, 'overall': 23},
            {'user': 'Mike', 'school': 'Purdue', 'round': 6, 'overall': 24}
        ]
        
        for pick in active_league_picks:
            school_result = db.execute(text("""
                SELECT id FROM schools WHERE name = :name LIMIT 1
            """), {'name': pick['school']})
            school_row = school_result.fetchone()
            
            if school_row:
                db.execute(text("""
                    INSERT INTO league_team_school_assignments 
                    (league_id, user_id, school_id, draft_round, draft_pick_overall)
                    VALUES (:league_id, :user_id, :school_id, :draft_round, :draft_pick_overall)
                """), {
                    'league_id': active_id,
                    'user_id': user_ids[pick['user']]['id'],
                    'school_id': school_row[0],
                    'draft_round': pick['round'],
                    'draft_pick_overall': pick['overall']
                })
        
        print("    ✅ Active league: Complete 24/24 picks, draft finished")
        print("✅ All leagues configured with proper draft states")
        
        db.commit()
        
        print("\n🎉 Mock data loaded successfully!")
        print("\n📋 Test Accounts (all password: test123):")
        for user in users:
            print(f"  📧 {user['email']} → {user['display_name']}")
        
        print("\n🏈 Test Leagues:")
        for name, info in league_ids.items():
            print(f"  🏆 {name}")
            print(f"     Join Code: {info['join_code']}")
            print(f"     Status: {info['status']}")
        
        print("\n🚀 Ready to test!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🏈 Pick6 Mock Data Loader")
    print("Creates test users, leagues, and teams")
    
    load_mock_data()
