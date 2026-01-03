#!/usr/bin/env python3
"""
Load schools data from local JSON file into the PRODUCTION database.
This script has production credentials embedded for convenience.
"""

import json
import os
import sys
import psycopg2
from typing import Dict, List

# Production database URL - embedded for convenience
PROD_DATABASE_URL = "postgresql://neondb_owner:npg_QFpa0ePGEn2K@ep-holy-bonus-adx50ti1-pooler.c-2.us-east-1.aws.neon.tech/pick6_prod?sslmode=require&channel_binding=require"

def load_teams_from_file(file_path: str) -> List[Dict]:
    """Load teams data from JSON file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Teams data file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        teams = json.load(f)
    
    print(f"✅ Loaded {len(teams)} teams from {file_path}")
    return teams

def create_school_slug(school_name: str) -> str:
    """Create a URL-friendly slug from school name"""
    return school_name.lower().replace(' ', '-').replace('&', 'and').replace('.', '')

def get_team_colors(team: Dict) -> tuple:
    """Extract primary and secondary colors from team data"""
    primary = team.get('color') or '#000000'
    secondary = team.get('alternateColor') or '#FFFFFF'
    
    # Handle null or invalid color values
    if primary == 'null' or primary == '#null' or not primary:
        primary = '#000000'
    if secondary == 'null' or secondary == '#null' or not secondary:
        secondary = '#FFFFFF'
    
    # Ensure colors have # prefix
    if not primary.startswith('#'):
        primary = f'#{primary}'
    if not secondary.startswith('#'):
        secondary = f'#{secondary}'
        
    return primary, secondary

def load_schools_to_database(teams: List[Dict], database_url: str, replace_existing: bool = False):
    """Load schools data into PostgreSQL database"""
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        # Check for existing data
        cur.execute('SELECT COUNT(*) FROM league_team_school_assignments;')
        assignments_count = cur.fetchone()[0]
        
        if replace_existing and assignments_count > 0:
            print(f"⚠️  Found {assignments_count} existing league assignments")
            choice = input("This will break existing leagues. Continue? (y/N): ")
            if choice.lower() != 'y':
                print("❌ Aborted by user")
                return
        
        # Clear existing data if requested
        if replace_existing:
            cur.execute('DELETE FROM schools;')
            print("🗑️  Cleared existing schools")
        else:
            cur.execute('SELECT COUNT(*) FROM schools;')
            existing_count = cur.fetchone()[0]
            print(f"📊 Found {existing_count} existing schools (will use CFB API IDs)")
        
        # Insert teams
        inserted_count = 0
        skipped_count = 0
        
        for i, team in enumerate(teams):
            try:
                # Use the CFB API ID from the JSON data instead of sequential numbering
                school_id = team.get('id')
                if not school_id:
                    print(f"⚠️  Skipping team {team.get('school', 'unknown')} - no CFB API ID")
                    skipped_count += 1
                    continue
                
                slug = create_school_slug(team.get('school', ''))
                primary_color, secondary_color = get_team_colors(team)
                
                # Handle null values properly
                abbreviation = team.get('abbreviation') or ''
                if abbreviation and len(abbreviation) > 10:
                    abbreviation = abbreviation[:10]
                
                cur.execute("""
                    INSERT INTO schools (id, team_slug, abbreviation, name, mascot, conference, primary_color, secondary_color)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        team_slug = EXCLUDED.team_slug,
                        abbreviation = EXCLUDED.abbreviation,
                        name = EXCLUDED.name,
                        mascot = EXCLUDED.mascot,
                        conference = EXCLUDED.conference,
                        primary_color = EXCLUDED.primary_color,
                        secondary_color = EXCLUDED.secondary_color
                """, (
                    school_id,
                    slug,
                    abbreviation,
                    team.get('school', ''),
                    team.get('mascot', ''),
                    team.get('conference', ''),
                    primary_color,
                    secondary_color
                ))
                
                # rowcount will be 1 for both INSERT and UPDATE
                inserted_count += 1
                    
            except Exception as e:
                print(f"❌ Error inserting {team.get('school', 'unknown')}: {e}")
                skipped_count += 1
        
        conn.commit()
        
        print(f"✅ Successfully inserted {inserted_count} schools")
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} schools (duplicates or errors)")
        
        # Show summary
        cur.execute('SELECT COUNT(*) FROM schools;')
        total = cur.fetchone()[0]
        print(f"📊 Total schools in database: {total}")
        
        # Check for our critical missing IDs
        missing_ids = [282, 304, 2710, 2306]
        cur.execute("SELECT id, name FROM schools WHERE id = ANY(%s)", (missing_ids,))
        found_schools = cur.fetchall()
        
        print(f"\n🎯 Critical school IDs check:")
        for school_id, name in found_schools:
            print(f"   ✅ ID {school_id}: {name}")
        
        found_ids = [row[0] for row in found_schools]
        still_missing = [id for id in missing_ids if id not in found_ids]
        if still_missing:
            print(f"   ❌ Still missing: {still_missing}")
        
        cur.execute("""
            SELECT conference, COUNT(*) 
            FROM schools 
            GROUP BY conference 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        """)
        conferences = cur.fetchall()
        print("\n🏆 Top conferences:")
        for conf, count in conferences:
            print(f"  {conf}: {count} teams")
    
    finally:
        cur.close()
        conn.close()

def main():
    """Main function"""
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, '..', 'data', 'cfb_teams_2025_complete.json')
    
    # Parse command line arguments
    replace_existing = '--replace' in sys.argv
    
    try:
        print("🏈 Loading CFB schools to PRODUCTION database...")
        print("🚨 WARNING: This will modify the PRODUCTION database!")
        print("=" * 60)
        
        # Confirm with user
        if not replace_existing:
            confirm = input("Continue loading schools to PRODUCTION? (y/N): ")
            if confirm.lower() != 'y':
                print("❌ Aborted by user")
                sys.exit(0)
        
        teams = load_teams_from_file(data_file)
        load_schools_to_database(teams, PROD_DATABASE_URL, replace_existing)
        print("\n🎉 Schools loading to PRODUCTION completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
