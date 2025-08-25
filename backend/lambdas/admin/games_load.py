import json
import sys
import os
import requests
from datetime import datetime
from typing import List, Dict

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from database import get_db_session, Game, School
from responses import success_response, error_response
from sqlalchemy import text

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"
CFB_API_KEY = os.getenv('CFB_API_KEY')

def fetch_games_from_api(year: str = "2024") -> List[Dict]:
    """Fetch all FBS games for a season from CollegeFootballData API"""
    if not CFB_API_KEY:
        raise Exception("CFB_API_KEY environment variable not set")
    
    headers = {'Authorization': f'Bearer {CFB_API_KEY}'}
    all_games = []
    
    try:
        # Get games for all weeks of the season (regular season: weeks 1-15, postseason: weeks 16-17)
        for week in range(1, 18):  # Weeks 1-17 to cover regular + postseason
            print(f"Fetching games for {year} week {week}...")
            
            response = requests.get(
                f"{CFB_API_BASE}/games",
                headers=headers,
                params={
                    'year': year,
                    'week': week,
                    'seasonType': 'regular' if week <= 15 else 'postseason',
                    'division': 'fbs'  # Only FBS games
                }
            )
            response.raise_for_status()
            games = response.json()
            
            if games:
                all_games.extend(games)
                print(f"  Found {len(games)} games for week {week}")
            else:
                print(f"  No games found for week {week}")
        
        print(f"Total games fetched for {year}: {len(all_games)}")
        return all_games
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games from API: {str(e)}")
        raise

def normalize_team_name(team_name: str) -> str:
    """Convert API team name to our normalized school ID"""
    if not team_name:
        return None
    
    # Use same normalization logic as season_init
    name = team_name.lower()
    name = name.replace(' university', '')
    name = name.replace(' state university', ' state')
    name = name.replace(' college', '')
    name = name.replace('university of ', '')
    name = name.replace(' ', '')
    name = name.replace('-', '')
    name = name.replace('.', '')
    
    # Handle special cases
    special_cases = {
        'ohiostate': 'ohiostate',
        'notredame': 'notredame',
        'texasam': 'texasam',
        'floridastate': 'floridastate',
        'virginiatech': 'virginiatech',
        'northcarolina': 'northcarolina',
        'southernmethodist': 'smu',
        'texaschristian': 'tcu',
        'brighamyoung': 'byu',
        'texasam': 'texasa&m'  # API has "Texas A&M"
    }
    
    return special_cases.get(name, name)

def lambda_handler(event, context):
    """Load all games for specified seasons"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        seasons = body.get('seasons', ['2024', '2025'])
        
        if isinstance(seasons, str):
            seasons = [seasons]
        
        print(f"Loading games for seasons: {seasons}")
        
        total_games_added = 0
        total_games_skipped = 0
        
        # Database operations
        db = get_db_session()
        try:
            for season in seasons:
                print(f"\n🏈 Loading games for {season} season...")
                
                # Fetch games from API
                api_games = fetch_games_from_api(season)
                
                if not api_games:
                    print(f"No games found for {season}")
                    continue
                
                games_added = 0
                games_skipped = 0
                
                for game in api_games:
                    try:
                        # Get team IDs directly from the API
                        home_team_id = game.get('homeId')
                        away_team_id = game.get('awayId')
                        
                        # Skip if we don't have team IDs
                        if not home_team_id or not away_team_id:
                            if games_skipped < 5:  # Only show first few for debugging
                                print(f"Debug: Missing team IDs - Home: {home_team_id}, Away: {away_team_id}")
                            games_skipped += 1
                            continue
                        
                        # Check if teams exist in our schools table
                        home_school = db.query(School).filter(School.id == home_team_id).first()
                        away_school = db.query(School).filter(School.id == away_team_id).first()
                        
                        if not home_school or not away_school:
                            if games_skipped < 5:  # Only show first few for debugging
                                print(f"Debug: Teams not in database - Home ID: {home_team_id} ({'found' if home_school else 'NOT FOUND'}), Away ID: {away_team_id} ({'found' if away_school else 'NOT FOUND'})")
                            games_skipped += 1
                            continue
                        
                        # Check if game already exists
                        existing_game = db.query(Game).filter(
                            Game.id == game.get('id')
                        ).first()
                        
                        if existing_game:
                            games_skipped += 1
                            continue
                        
                        # Parse game time
                        start_date = None
                        if game.get('startDate'):
                            try:
                                start_date = datetime.fromisoformat(game['startDate'].replace('Z', '+00:00'))
                            except ValueError:
                                pass
                        
                        # Create game record with all API fields
                        new_game = Game(
                            id=game.get('id'),
                            season=game.get('season'),
                            week=game.get('week'),
                            season_type=game.get('seasonType', 'regular'),
                            start_date=start_date,
                            start_time_tbd=game.get('startTimeTBD', False),
                            completed=game.get('completed', False),
                            neutral_site=game.get('neutralSite', False),
                            conference_game=game.get('conferenceGame', False),
                            attendance=game.get('attendance'),
                            venue_id=game.get('venueId'),
                            venue=game.get('venue'),
                            home_id=home_team_id,
                            home_team=game.get('homeTeam'),
                            home_classification=game.get('homeClassification'),
                            home_conference=game.get('homeConference'),
                            home_points=game.get('homePoints', 0),
                            home_line_scores=game.get('homeLineScores', []),
                            home_postgame_win_probability=game.get('homePostgameWinProbability'),
                            home_pregame_elo=game.get('homePregameElo'),
                            home_postgame_elo=game.get('homePostgameElo'),
                            away_id=away_team_id,
                            away_team=game.get('awayTeam'),
                            away_classification=game.get('awayClassification'),
                            away_conference=game.get('awayConference'),
                            away_points=game.get('awayPoints', 0),
                            away_line_scores=game.get('awayLineScores', []),
                            away_postgame_win_probability=game.get('awayPostgameWinProbability'),
                            away_pregame_elo=game.get('awayPregameElo'),
                            away_postgame_elo=game.get('awayPostgameElo'),
                            excitement_index=game.get('excitementIndex'),
                            highlights=game.get('highlights'),
                            notes=game.get('notes')
                        )
                        
                        db.add(new_game)
                        games_added += 1
                        
                        if games_added % 100 == 0:
                            print(f"  Added {games_added} games so far...")
                        
                    except Exception as e:
                        print(f"Error adding game {game.get('id', 'Unknown')}: {str(e)}")
                        games_skipped += 1
                        continue
                
                # Commit games for this season
                db.commit()
                
                print(f"✅ {season} season complete!")
                print(f"   Games added: {games_added}")
                print(f"   Games skipped: {games_skipped}")
                
                total_games_added += games_added
                total_games_skipped += games_skipped
            
            return success_response({
                'seasons': seasons,
                'total_games_added': total_games_added,
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
