import json
import sys
import os
import requests
from datetime import datetime
from typing import List, Dict

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.database import get_db_session, Game, School
from shared.responses import success_response, error_response
from shared.parameter_store import get_cfb_api_key
from shared.week_utils import get_all_api_week_params_for_season
from shared.game_utils import process_api_game, validate_game_teams, create_new_game, update_existing_game
from sqlalchemy import text

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"

def fetch_games_from_api(year: str = "2024", from_week: int = 1) -> List[Dict]:
    """Fetch FBS games for a season from CollegeFootballData API
    
    Uses shared week mapping from week_utils.get_all_api_week_params_for_season()
    to ensure consistent week numbering across all game loaders.
    
    Note: The API uses SEPARATE week numbering for regular vs postseason:
    - Regular season: weeks 1-14 (seasonType=regular)
    - Week 15: Conference Championships (API regular weeks 15-16)
    - Weeks 16-21: Bowl/CFP (API postseason weeks 1-6)
    """
    cfb_api_key = get_cfb_api_key()
    if not cfb_api_key:
        raise Exception("CFB_API_KEY not available in Parameter Store")
    
    headers = {'Authorization': f'Bearer {cfb_api_key}'}
    all_games = []
    
    try:
        print(f"Fetching games from week {from_week} onward...")
        
        # Use shared week mapping for consistency
        week_params = get_all_api_week_params_for_season()
        
        for internal_week, api_week, season_type in week_params:
            # Skip weeks before from_week
            if internal_week < from_week:
                continue
            
            print(f"Fetching {season_type} games for {year} (API week {api_week} -> our week {internal_week})...")
            
            response = requests.get(
                f"{CFB_API_BASE}/games",
                headers=headers,
                params={
                    'year': year,
                    'week': api_week,
                    'seasonType': season_type,
                    'division': 'fbs'
                }
            )
            response.raise_for_status()
            games = response.json()
            
            if games:
                # Set our internal week number on each game
                for game in games:
                    game['week'] = internal_week
                all_games.extend(games)
                print(f"  Found {len(games)} games")
            else:
                print(f"  No games found")
        
        print(f"Total games fetched for {year}: {len(all_games)}")
        return all_games
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games from API: {str(e)}")
        raise

def lambda_handler(event, context):
    """Load all games for specified seasons
    
    Uses shared game processing functions for consistency with scheduled loader.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        seasons = body.get('seasons', ['2024', '2025'])
        delete_from_week = body.get('delete_from_week')  # Optional: delete games from this week onward first
        skip_existing = body.get('skip_existing', True)  # If False, update existing games instead of skipping
        from_week = body.get('from_week', 1)  # Optional: only load games from this week onward
        
        if isinstance(seasons, str):
            seasons = [seasons]
        
        print(f"Loading games for seasons: {seasons}")
        print(f"From week: {from_week}")
        print(f"Skip existing: {skip_existing} (set skip_existing=false to update existing games)")
        
        total_games_added = 0
        total_games_updated = 0
        total_games_skipped = 0
        total_games_deleted = 0
        
        # Database operations
        db = get_db_session()
        try:
            # Delete games from specified week onward if requested
            if delete_from_week:
                for season in seasons:
                    delete_query = text("""
                        DELETE FROM games 
                        WHERE season = :season AND week >= :week
                    """)
                    result = db.execute(delete_query, {'season': int(season), 'week': int(delete_from_week)})
                    deleted = result.rowcount
                    total_games_deleted += deleted
                    print(f"🗑️ Deleted {deleted} games from {season} season week {delete_from_week}+")
                db.commit()
            
            for season in seasons:
                print(f"\n🏈 Loading games for {season} season...")
                
                # Fetch games from API
                api_games = fetch_games_from_api(season, from_week)
                
                if not api_games:
                    print(f"No games found for {season}")
                    continue
                
                games_added = 0
                games_updated = 0
                games_skipped = 0
                
                for game in api_games:
                    # Use shared game processing function
                    # Note: game already has 'week' set to internal week by fetch_games_from_api
                    result = process_api_game(db, game, internal_week=game.get('week'), skip_existing=skip_existing)
                    
                    if result == 'added':
                        games_added += 1
                    elif result == 'updated':
                        games_updated += 1
                    else:
                        games_skipped += 1
                    
                    if (games_added + games_updated) % 100 == 0 and (games_added + games_updated) > 0:
                        print(f"  Processed {games_added + games_updated} games so far...")
                
                # Commit games for this season
                db.commit()
                
                print(f"✅ {season} season complete!")
                print(f"   Games added: {games_added}")
                print(f"   Games updated: {games_updated}")
                print(f"   Games skipped: {games_skipped}")
                
                total_games_added += games_added
                total_games_updated += games_updated
                total_games_skipped += games_skipped
            
            return success_response({
                'seasons': seasons,
                'total_games_deleted': total_games_deleted,
                'total_games_added': total_games_added,
                'total_games_updated': total_games_updated,
                'total_games_skipped': total_games_skipped,
                'message': f'Successfully loaded games for {len(seasons)} seasons'
            })
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        print(f"Games loading error: {str(e)}")
        return error_response(f'Games loading failed: {str(e)}', 500)
