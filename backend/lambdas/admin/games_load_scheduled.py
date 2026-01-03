import json
import sys
import os
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.database import get_db_session, Game, School
from shared.responses import success_response, error_response
from shared.parameter_store import get_cfb_api_key
from shared.week_utils import get_current_week_of_season, get_api_week_params
from shared.game_utils import process_api_game

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"


def fetch_week_games_from_api(season: int, internal_week: int) -> Tuple[List[Dict], int]:
    """
    Fetch games for a specific week from CollegeFootballData API
    
    Uses shared get_api_week_params() for CONSISTENT week mapping across all loaders.
    
    Args:
        season: The season year
        internal_week: Our internal week number (1-21)
        
    Returns:
        Tuple of (games list, internal_week)
    """
    cfb_api_key = get_cfb_api_key()
    if not cfb_api_key:
        raise Exception("CFB_API_KEY not available in Parameter Store")
    
    headers = {'Authorization': f'Bearer {cfb_api_key}'}
    all_games = []
    
    try:
        # Use shared week mapping for consistency with bulk loader
        week_params = get_api_week_params(internal_week)
        
        for api_week, season_type, description in week_params:
            print(f"Fetching {description} for {season}...")
            
            response = requests.get(
                f"{CFB_API_BASE}/games",
                headers=headers,
                params={
                    'year': season,
                    'week': api_week,
                    'seasonType': season_type,
                    'division': 'fbs'
                }
            )
            response.raise_for_status()
            games = response.json()
            
            # Set our internal week number on each game
            for game in games:
                game['week'] = internal_week
            
            all_games.extend(games)
            print(f"  Found {len(games)} games")
        
        print(f"Total: {len(all_games)} games for week {internal_week}")
        return all_games, internal_week
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games from API: {str(e)}")
        raise


def get_current_week_games(season: int = None) -> Tuple[List[Dict], int]:
    """
    Fetch games for the current week from CollegeFootballData API
    
    Uses shared week detection and mapping for consistency.
    """
    # Default to current season if not specified
    if not season:
        season = datetime.now().year
        if datetime.now().month < 8:
            season -= 1
    
    # Get current week using shared function
    current_week = get_current_week_of_season(season)
    
    # Fetch games for that week
    return fetch_week_games_from_api(season, current_week)


def is_saturday_cst() -> bool:
    """
    Check if current time is Saturday in Central Time
    College football games are primarily on Saturdays
    """
    utc_now = datetime.now(timezone.utc)
    cst_offset = timedelta(hours=-6)
    cst_now = utc_now + cst_offset
    return cst_now.weekday() == 5

def lambda_handler(event, context):
    """
    Scheduled game loader - updates only current week games
    Designed to be called by EventBridge on a schedule
    
    Uses shared game processing functions for consistency with bulk loader.
    """
    try:
        # Parse any manual parameters from event
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])
        elif isinstance(event, dict) and 'season' in event:
            # Direct invocation with parameters
            body = event
        
        season = body.get('season')
        force_all_weeks = body.get('force_all_weeks', False)
        
        # Default to current season
        if not season:
            season = datetime.now().year
            if datetime.now().month < 8:  # Before August, likely previous season
                season -= 1
        
        print(f"🏈 Scheduled game update starting for {season} season...")
        print(f"   Current time: {datetime.now(timezone.utc).isoformat()}")
        print(f"   Is Saturday CST: {is_saturday_cst()}")
        
        # If force_all_weeks is true, fall back to full games_load logic
        if force_all_weeks:
            print("⚠️ Force all weeks requested - this should use the bulk games_load endpoint instead")
            return error_response("Use /admin/games/load for bulk loading all weeks", 400)
        
        # Check if a specific week was requested
        target_week = body.get('week')
        if target_week:
            # Manual week specified - load that specific week
            print(f"🎯 Loading specific week: {target_week}")
            api_games, current_week = fetch_week_games_from_api(season, int(target_week))
        else:
            # Auto-detect current week
            api_games, current_week = get_current_week_games(season)
        
        if not api_games:
            return success_response({
                'season': season,
                'week': current_week,
                'games_updated': 0,
                'games_added': 0,
                'message': f'No games found for {season} week {current_week}'
            })
        
        # Database operations
        db = get_db_session()
        games_updated = 0
        games_added = 0
        games_skipped = 0
        
        try:
            for game in api_games:
                # Use shared game processing function (never skip existing - always update)
                result = process_api_game(db, game, internal_week=current_week, skip_existing=False)
                
                if result == 'added':
                    games_added += 1
                elif result == 'updated':
                    games_updated += 1
                else:
                    games_skipped += 1
            
            # Commit all changes
            db.commit()
            
            return success_response({
                'season': season,
                'week': current_week,
                'games_updated': games_updated,
                'games_added': games_added,
                'games_skipped': games_skipped,
                'total_api_games': len(api_games),
                'is_saturday_cst': is_saturday_cst(),
                'message': f'Successfully processed week {current_week} games for {season} season - {games_updated + games_added} games processed, {games_skipped} skipped'
            })
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        print(f"Scheduled games update error: {str(e)}")
        return error_response(f'Scheduled games update failed: {str(e)}', 500)
