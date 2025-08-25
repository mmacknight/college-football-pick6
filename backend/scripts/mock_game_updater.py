#!/usr/bin/env python3
"""
Mock Game Updater - Simulates live game updates for testing
Uses the existing load_games functionality and current week detection for 2025 season

Usage:
  python mock_game_updater.py           # Use real CFB API data
  python mock_game_updater.py --live    # Generate mock scores for testing
"""

import os
import sys
import json
import random
import time
import argparse
from datetime import datetime

# Add the parent directory to sys.path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from local-env.json (same as dev_server.py does)
def load_local_env():
    """Load environment variables from local-env.json"""
    env_file = os.path.join(os.path.dirname(__file__), '..', 'local-env.json')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_data = json.load(f)
            for key, value in env_data.get('Parameters', {}).items():
                os.environ[key] = value
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️ Environment file not found: {env_file}")

# Load environment first
load_local_env()

# Import from lambdas
from lambdas.admin.games_load import lambda_handler as games_load_handler
from lambdas.shared.week_utils import get_current_week_of_season, get_week_info
from lambdas.shared.database import get_db_session, Game, School
from sqlalchemy import and_, or_

def load_current_week_games_from_api(season=2025):
    """Load REAL games for current week only from CFB API"""
    try:
        # Get current week first
        current_week = get_current_week_of_season(season)
        print(f"🏈 Fetching REAL games from CFB API for {season} season, week {current_week}...")
        
        # Import the games loading function
        from lambdas.admin.games_load import fetch_games_from_api
        import requests
        
        # Get CFB API key
        CFB_API_KEY = os.getenv('CFB_API_KEY')
        if not CFB_API_KEY:
            print("❌ CFB_API_KEY not found")
            return False
        
        # Fetch current week games from API (including FBS vs FCS games)
        headers = {'Authorization': f'Bearer {CFB_API_KEY}'}
        response = requests.get(
            f"https://api.collegefootballdata.com/games",
            headers=headers,
            params={
                'year': season,
                'week': current_week,
                'seasonType': 'regular'
                # Removed 'division': 'fbs' to include FBS vs FCS games
            }
        )
        response.raise_for_status()
        api_games = response.json()
        
        print(f"✅ Fetched {len(api_games)} real games from CFB API for week {current_week}")
        
        # Update database with real scores
        if api_games:
            update_games_in_database(api_games, season, live_mode=False)
        
        return True
            
    except Exception as e:
        print(f"❌ Failed to fetch real games: {str(e)}")
        return False

def update_games_in_database(api_games, season, live_mode=False):
    """Update database with real scores from API or mock data for testing"""
    db = get_db_session()
    
    try:
        updated_count = 0
        
        for api_game in api_games:
            # Find the game in our database
            game = db.query(Game).filter(Game.id == api_game.get('id')).first()
            
            if game:
                old_completed = game.completed
                
                if live_mode:
                    # Generate mock scores for testing
                    if random.random() < 0.7:  # 70% chance to have a score update
                        # Generate realistic scores (0-49 range)
                        game.home_points = random.randint(0, 49)
                        game.away_points = random.randint(0, 49)
                        # 40% chance to mark as completed
                        game.completed = random.random() < 0.4
                    else:
                        # Keep existing scores or set to 0
                        game.home_points = game.home_points or 0
                        game.away_points = game.away_points or 0
                else:
                    # Update with real data from API
                    game.home_points = api_game.get('homePoints', 0)
                    game.away_points = api_game.get('awayPoints', 0)
                    game.completed = api_game.get('completed', False)
                
                # Log if status changed
                if not old_completed and game.completed:
                    home_team = db.query(School).filter(School.id == game.home_id).first()
                    away_team = db.query(School).filter(School.id == game.away_id).first()
                    home_name = home_team.name if home_team else "Team"
                    away_name = away_team.name if away_team else "Team"
                    mode_prefix = "🎮 MOCK" if live_mode else "🏁"
                    print(f"{mode_prefix} FINAL: {away_name} {game.away_points or 0} - {game.home_points or 0} {home_name}")
                elif (game.home_points or 0) > 0 or (game.away_points or 0) > 0:
                    home_team = db.query(School).filter(School.id == game.home_id).first()
                    away_team = db.query(School).filter(School.id == game.away_id).first()
                    home_name = home_team.name if home_team else "Team"
                    away_name = away_team.name if away_team else "Team"
                    status = "FINAL" if game.completed else "IN PROGRESS"
                    mode_prefix = "🎮 MOCK" if live_mode else "🏈"
                    print(f"{mode_prefix} {status}: {away_name} {game.away_points or 0} - {game.home_points or 0} {home_name}")
                
                updated_count += 1
        
        db.commit()
        data_source = "mock data" if live_mode else "real data from CFB API"
        print(f"✅ Updated {updated_count} games with {data_source}")
        
    except Exception as e:
        print(f"❌ Error updating games: {e}")
        db.rollback()
    finally:
        db.close()

def get_current_week_games(season=2025):
    """Get games for the current week of the season"""
    try:
        current_week = get_current_week_of_season(season)
        print(f"📅 Current week for {season} season: Week {current_week}")
        
        week_info = get_week_info(current_week, season)
        print(f"📊 Week {current_week} info:")
        print(f"   Date range: {week_info['dateRange']}")
        print(f"   Total games: {week_info['totalGames']}")
        print(f"   Completed games: {week_info['completedGames']}")
        print(f"   Is current: {week_info['isCurrent']}")
        print(f"   Is complete: {week_info['isComplete']}")
        
        # Get actual games from database
        db = get_db_session()
        try:
            games = db.query(Game).filter(
                and_(Game.season == season, Game.week == current_week)
            ).all()
            
            print(f"🎮 Found {len(games)} games in database for Week {current_week}")
            return games, current_week
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error getting current week games: {e}")
        return [], 1

def simulate_game_updates(games, max_updates=2):
    """Simulate live score updates for random games"""
    if not games:
        print("⚠️ No games available to update")
        return []
    
    print(f"🎮 Found {len(games)} total games in current week")
    
    # Filter for incomplete games or simulate some completed ones
    incomplete_games = [g for g in games if not g.completed]
    print(f"📊 {len(incomplete_games)} incomplete games, {len(games) - len(incomplete_games)} completed games")
    
    if not incomplete_games and len(games) > 0:
        print("📋 All games are completed. Using random completed games for simulation...")
        incomplete_games = random.sample(games, min(len(games), max_updates))
    elif len(incomplete_games) == 0:
        print("⚠️ No games found to update")
        return []
    
    # Select random games to update
    games_to_update = random.sample(incomplete_games, min(len(incomplete_games), max_updates))
    
    print(f"🎲 Simulating score updates for {len(games_to_update)} games...")
    
    updated_games = []
    db = get_db_session()
    
    try:
        for i, game in enumerate(games_to_update, 1):
            print(f"  Processing game {i}/{len(games_to_update)}...")
            # Get team names for logging
            home_team = db.query(School).filter(School.id == game.home_id).first()
            away_team = db.query(School).filter(School.id == game.away_id).first()
            
            home_name = home_team.name if home_team else "Team"
            away_name = away_team.name if away_team else "Team"
            
            # Generate realistic scores
            if game.completed:
                # Just update an already completed game for demo
                print(f"📊 Refreshing completed game: {away_name} vs {home_name}")
            else:
                # Simulate a game in progress or completing
                old_home_score = game.home_points or 0
                old_away_score = game.away_points or 0
                
                # Add some points (0-21 range for realism)
                home_addition = random.randint(0, 21)
                away_addition = random.randint(0, 21)
                
                game.home_points = old_home_score + home_addition
                game.away_points = old_away_score + away_addition
                
                # Randomly mark some games as completed
                if random.random() < 0.3:  # 30% chance to complete
                    game.completed = True
                    status = "FINAL"
                else:
                    status = "IN PROGRESS"
                
                print(f"🏈 {status}: {away_name} {game.away_points} - {game.home_points} {home_name}")
                
                # Commit the update
                db.commit()
                
                updated_games.append({
                    'id': game.id,
                    'week': game.week,
                    'homeTeam': {
                        'id': home_team.id,
                        'name': home_name,
                        'mascot': home_team.mascot,
                        'primaryColor': home_team.primary_color
                    } if home_team else None,
                    'awayTeam': {
                        'id': away_team.id,
                        'name': away_name,
                        'mascot': away_team.mascot,
                        'primaryColor': away_team.primary_color
                    } if away_team else None,
                    'score': {
                        'home': game.home_points,
                        'away': game.away_points
                    },
                    'completed': game.completed,
                    'status': status
                })
        
        return updated_games
        
    except Exception as e:
        print(f"❌ Error updating games: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def trigger_standings_update():
    """Trigger a simple standings update for testing"""
    print("📊 Simulating standings update broadcast...")
    
    try:
        # For local testing, just simulate the broadcast
        # In a real environment, this would trigger the actual updater
        print("✅ Standings update simulation complete!")
        print("   (In production, this would broadcast to WebSocket connections)")
        return True
            
    except Exception as e:
        print(f"❌ Error in standings update simulation: {e}")
        return False

def load_current_week_games_with_mock(season=2025):
    """Load games for current week and generate mock scores for testing"""
    try:
        current_week = get_current_week_of_season(season)
        print(f"🎮 Generating MOCK scores for {season} season, week {current_week}...")
        
        import requests
        
        # Get CFB API key
        CFB_API_KEY = os.getenv('CFB_API_KEY')
        if not CFB_API_KEY:
            print("❌ CFB_API_KEY not found")
            return False
        
        # Fetch current week games from API (just for the game list)
        headers = {'Authorization': f'Bearer {CFB_API_KEY}'}
        response = requests.get(
            f"https://api.collegefootballdata.com/games",
            headers=headers,
            params={
                'year': season,
                'week': current_week,
                'seasonType': 'regular'
            }
        )
        response.raise_for_status()
        api_games = response.json()
        
        print(f"✅ Fetched {len(api_games)} games from CFB API for mock scoring")
        
        # Update database with mock scores
        if api_games:
            update_games_in_database(api_games, season, live_mode=True)
        
        return True
            
    except Exception as e:
        print(f"❌ Failed to generate mock scores: {str(e)}")
        return False

def run_single_update(live_mode=False):
    """Run a single update cycle with REAL or MOCK data"""
    print(f"⏰ Update Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if live_mode:
        # Step 1: Generate mock game data for testing
        success = load_current_week_games_with_mock(2025)
        data_type = "Mock game data"
    else:
        # Step 1: Fetch real game data from CFB API
        success = load_current_week_games_from_api(2025)
        data_type = "Real game data"
    
    if success:
        print(f"✅ {data_type} updated!")
        
        # Step 2: Trigger standings update
        trigger_standings_update()
        return True
    else:
        print(f"⚠️ No {data_type.lower()} updates available")
        return False

def main():
    """Main function to run the mock game updater in a loop"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Mock Game Updater for Pick6')
    parser.add_argument('--live', action='store_true', 
                       help='Generate mock scores for testing instead of using real CFB API data')
    args = parser.parse_args()
    
    mode = "LIVE TESTING" if args.live else "REAL DATA"
    data_source = "mock scores" if args.live else "CFB API"
    
    print(f"🎮 Mock Game Updater for Pick6 - {mode} Mode")
    print("=" * 60)
    print(f"🗓️ Target Season: 2025")
    print(f"📊 Data Source: {data_source}")
    print(f"🔄 Running every 30 seconds")
    print(f"⏹️  Press Ctrl+C to stop")
    print("=" * 60)
    
    # Initial setup - just verify we can get current week
    try:
        current_week = get_current_week_of_season(2025)
        print(f"✅ Current week detected: Week {current_week}")
    except Exception as e:
        print(f"❌ Failed to get current week: {e}")
        return 1
    
    update_count = 0
    
    try:
        while True:
            update_count += 1
            print(f"\n🔄 Update #{update_count}")
            print("-" * 30)
            
            success = run_single_update(live_mode=args.live)
            
            if success:
                print("✅ Update cycle complete!")
            else:
                print("⚠️ Update cycle had no changes")
            
            print(f"😴 Waiting 30 seconds for next update...")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Stopped by user after {update_count} updates")
        print("✅ Mock game updater shutdown complete!")
        return 0
    except Exception as e:
        print(f"\n❌ Error in update loop: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
