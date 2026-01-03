#!/usr/bin/env python3
"""
Direct script to load 2025 CFB games from CollegeFootballData API
Points directly to production database
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict

# Add the layers/shared/python to the path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layers', 'shared', 'python'))

from shared.database import get_db_session, Game, School
# from shared.parameter_store import get_cfb_api_key

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"

def fetch_games_from_api(year: str = "2025") -> List[Dict]:
    """Fetch all FBS games for a season from CollegeFootballData API"""
    cfb_api_key = os.getenv('CFB_API_KEY')
    if not cfb_api_key:
        raise Exception("CFB_API_KEY environment variable not set")
    
    headers = {'Authorization': f'Bearer {cfb_api_key}'}
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

def main():
    print("🏈 Loading College Football Games for 2025...")
    print("=" * 50)
    
    try:
        # Fetch games from API
        print("📡 Fetching games from CollegeFootballData API...")
        api_games = fetch_games_from_api("2025")
        
        # Database operations
        print("💾 Connecting to database...")
        db = get_db_session()
        
        games_added = 0
        games_skipped = 0
        
        try:
            for game in api_games:
                try:
                    # Get team IDs directly from the API
                    home_team_id = game.get('homeId')
                    away_team_id = game.get('awayId')
                    
                    # Skip if we don't have team IDs
                    if not home_team_id or not away_team_id:
                        games_skipped += 1
                        continue
                    
                    # Check if BOTH teams exist in our schools table (required for foreign keys)
                    home_school = db.query(School).filter(School.id == home_team_id).first()
                    away_school = db.query(School).filter(School.id == away_team_id).first()
                    
                    if not home_school or not away_school:
                        # Skip games with FCS teams or teams not in our database
                        if games_skipped < 5:  # Only show first few for debugging
                            missing_teams = []
                            if not home_school:
                                missing_teams.append(f"Home ID: {home_team_id}")
                            if not away_school:
                                missing_teams.append(f"Away ID: {away_team_id}")
                            print(f"  Skipping game - Missing teams: {', '.join(missing_teams)}")
                        games_skipped += 1
                        continue
                    
                    # Check if game already exists
                    existing_game = db.query(Game).filter(Game.id == game.get('id')).first()
                    if existing_game:
                        games_skipped += 1
                        continue
                    
                    # Parse game time
                    start_date = None
                    if game.get('startDate'):
                        try:
                            start_date = datetime.fromisoformat(game['startDate'].replace('Z', '+00:00'))
                        except ValueError:
                            start_date = None
                    
                    # Create new game record
                    new_game = Game(
                        id=game.get('id'),
                        season=int(game.get('season', 2025)),
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
                        home_classification=game.get('homeClassification', 'fbs'),
                        home_conference=game.get('homeConference'),
                        home_points=game.get('homePoints'),
                        home_line_scores=game.get('homeLineScores', []),
                        home_postgame_win_probability=game.get('homePostgameWinProbability'),
                        home_pregame_elo=game.get('homePregameElo'),
                        home_postgame_elo=game.get('homePostgameElo'),
                        away_id=away_team_id,
                        away_team=game.get('awayTeam'),
                        away_classification=game.get('awayClassification', 'fbs'),
                        away_conference=game.get('awayConference'),
                        away_points=game.get('awayPoints'),
                        away_line_scores=game.get('awayLineScores', []),
                        away_postgame_win_probability=game.get('awayPostgameWinProbability'),
                        away_pregame_elo=game.get('awayPregameElo'),
                        away_postgame_elo=game.get('awayPostgameElo'),
                        excitement_index=game.get('excitementIndex'),
                        highlights=game.get('highlights'),
                        notes=game.get('notes'),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.add(new_game)
                    games_added += 1
                    
                    # Commit every 100 games
                    if games_added % 100 == 0:
                        db.commit()
                        print(f"  Committed {games_added} games...")
                        
                except Exception as game_error:
                    print(f"Error processing game {game.get('id')}: {str(game_error)}")
                    games_skipped += 1
                    continue
            
            # Final commit
            db.commit()
            
            print("\n✅ Games loading completed!")
            print(f"   Games added: {games_added}")
            print(f"   Games skipped: {games_skipped}")
            print(f"   Total API games: {len(api_games)}")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Failed to load games: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
