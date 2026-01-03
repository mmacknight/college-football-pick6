"""
Shared game processing utilities for loading and updating games from CFB API
"""
from datetime import datetime
from typing import Dict, Optional, Tuple
from shared.database import Game, School


def parse_game_start_date(date_string: str) -> Optional[datetime]:
    """
    Parse game start date from API format to datetime
    
    Args:
        date_string: ISO format date string from API (e.g., "2024-09-07T00:00:00.000Z")
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except ValueError:
        return None


def validate_game_teams(db, home_team_id: int, away_team_id: int) -> Tuple[bool, Optional[School], Optional[School]]:
    """
    Validate that both teams exist in our schools table
    
    Args:
        db: Database session
        home_team_id: Home team's school ID
        away_team_id: Away team's school ID
        
    Returns:
        Tuple of (is_valid, home_school, away_school)
    """
    if not home_team_id or not away_team_id:
        return False, None, None
    
    home_school = db.query(School).filter(School.id == home_team_id).first()
    away_school = db.query(School).filter(School.id == away_team_id).first()
    
    is_valid = home_school is not None and away_school is not None
    return is_valid, home_school, away_school


def update_existing_game(existing_game: Game, api_game: Dict, start_date: datetime = None) -> None:
    """
    Update an existing game record with latest data from API
    
    Args:
        existing_game: The existing Game ORM object
        api_game: Game data dictionary from CFB API
        start_date: Pre-parsed start date (optional, will parse from api_game if not provided)
    """
    if start_date is None:
        start_date = parse_game_start_date(api_game.get('startDate'))
    
    # Update fields that may have changed
    if 'week' in api_game:
        existing_game.week = api_game['week']
    if 'seasonType' in api_game:
        existing_game.season_type = api_game['seasonType']
    if start_date:
        existing_game.start_date = start_date
    
    existing_game.start_time_tbd = api_game.get('startTimeTBD', existing_game.start_time_tbd)
    existing_game.completed = api_game.get('completed', existing_game.completed)
    existing_game.home_points = api_game.get('homePoints', existing_game.home_points)
    existing_game.away_points = api_game.get('awayPoints', existing_game.away_points)
    existing_game.home_line_scores = api_game.get('homeLineScores', existing_game.home_line_scores)
    existing_game.away_line_scores = api_game.get('awayLineScores', existing_game.away_line_scores)
    existing_game.attendance = api_game.get('attendance', existing_game.attendance)
    existing_game.excitement_index = api_game.get('excitementIndex', existing_game.excitement_index)
    existing_game.highlights = api_game.get('highlights', existing_game.highlights)
    existing_game.notes = api_game.get('notes', existing_game.notes)
    
    # Update postgame stats if available
    if 'homePostgameWinProbability' in api_game:
        existing_game.home_postgame_win_probability = api_game['homePostgameWinProbability']
    if 'awayPostgameWinProbability' in api_game:
        existing_game.away_postgame_win_probability = api_game['awayPostgameWinProbability']
    if 'homePostgameElo' in api_game:
        existing_game.home_postgame_elo = api_game['homePostgameElo']
    if 'awayPostgameElo' in api_game:
        existing_game.away_postgame_elo = api_game['awayPostgameElo']


def create_new_game(api_game: Dict, internal_week: int = None) -> Game:
    """
    Create a new Game record from API data
    
    Args:
        api_game: Game data dictionary from CFB API
        internal_week: Override week number (for postseason mapping)
        
    Returns:
        New Game ORM object (not yet added to session)
    """
    start_date = parse_game_start_date(api_game.get('startDate'))
    
    # Use internal_week if provided (for postseason mapping), otherwise use API week
    week = internal_week if internal_week is not None else api_game.get('week')
    
    return Game(
        id=api_game.get('id'),
        season=api_game.get('season'),
        week=week,
        season_type=api_game.get('seasonType', 'regular'),
        start_date=start_date,
        start_time_tbd=api_game.get('startTimeTBD', False),
        completed=api_game.get('completed', False),
        neutral_site=api_game.get('neutralSite', False),
        conference_game=api_game.get('conferenceGame', False),
        attendance=api_game.get('attendance'),
        venue_id=api_game.get('venueId'),
        venue=api_game.get('venue'),
        home_id=api_game.get('homeId'),
        home_team=api_game.get('homeTeam'),
        home_classification=api_game.get('homeClassification'),
        home_conference=api_game.get('homeConference'),
        home_points=api_game.get('homePoints', 0),
        home_line_scores=api_game.get('homeLineScores', []),
        home_postgame_win_probability=api_game.get('homePostgameWinProbability'),
        home_pregame_elo=api_game.get('homePregameElo'),
        home_postgame_elo=api_game.get('homePostgameElo'),
        away_id=api_game.get('awayId'),
        away_team=api_game.get('awayTeam'),
        away_classification=api_game.get('awayClassification'),
        away_conference=api_game.get('awayConference'),
        away_points=api_game.get('awayPoints', 0),
        away_line_scores=api_game.get('awayLineScores', []),
        away_postgame_win_probability=api_game.get('awayPostgameWinProbability'),
        away_pregame_elo=api_game.get('awayPregameElo'),
        away_postgame_elo=api_game.get('awayPostgameElo'),
        excitement_index=api_game.get('excitementIndex'),
        highlights=api_game.get('highlights'),
        notes=api_game.get('notes')
    )


def process_api_game(db, api_game: Dict, internal_week: int = None, skip_existing: bool = False) -> str:
    """
    Process a single game from the API - either update existing or create new
    
    Uses a savepoint (begin_nested) for each game so that one failed game
    doesn't roll back all other successful updates. This prevents all-or-nothing failures.
    
    Args:
        db: Database session
        api_game: Game data dictionary from CFB API
        internal_week: Override week number (for postseason mapping)
        skip_existing: If True, skip games that already exist (faster for bulk loads)
        
    Returns:
        str: 'added', 'updated', 'skipped', or 'error'
    """
    home_team_id = api_game.get('homeId')
    away_team_id = api_game.get('awayId')
    
    # Validate teams exist BEFORE starting a savepoint
    is_valid, home_school, away_school = validate_game_teams(db, home_team_id, away_team_id)
    if not is_valid:
        return 'skipped'
    
    # Check if game already exists
    existing_game = db.query(Game).filter(Game.id == api_game.get('id')).first()
    
    # Use a savepoint so this game's failure doesn't affect others
    try:
        savepoint = db.begin_nested()
        
        if existing_game:
            if skip_existing:
                return 'skipped'
            else:
                # Set internal week on api_game for update
                if internal_week is not None:
                    api_game['week'] = internal_week
                update_existing_game(existing_game, api_game)
                savepoint.commit()
                return 'updated'
        else:
            new_game = create_new_game(api_game, internal_week)
            db.add(new_game)
            savepoint.commit()
            return 'added'
            
    except Exception as e:
        # Only rolls back to the savepoint, not the entire transaction
        savepoint.rollback()
        print(f"Error processing game {api_game.get('id', 'Unknown')}: {str(e)}")
        return 'error'
