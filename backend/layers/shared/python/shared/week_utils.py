"""
Week detection and management utilities for college football seasons
"""
from datetime import datetime, timedelta
from shared.database import get_db_session, Game
from sqlalchemy import text

def get_current_week_of_season(season):
    """
    Dynamically determine the current week based on game data
    REQUIRES season parameter - no defaults
    
    Args:
        season (int): The season year (e.g., 2024)
        
    Returns:
        int: Current week number (1-20, where 16-20 are postseason/bowls)
        
    Raises:
        ValueError: If season is not provided
        
    Week mapping:
    - Weeks 1-15: Regular season
    - Week 16: Conference Championships  
    - Week 17-20: Bowl games, CFP
    """
    if not season:
        raise ValueError("Season parameter is required")
    
    db = get_db_session()
    
    try:
        # Complex query to find the "current" week for the specific season
        # Extended to week 20 to handle all bowl games
        query = text("""
            WITH week_analysis AS (
                SELECT 
                    week,
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN completed = true THEN 1 END) as completed_games,
                    COUNT(CASE WHEN start_date BETWEEN NOW() - INTERVAL '2 days' 
                                              AND NOW() + INTERVAL '5 days' THEN 1 END) as current_games,
                    MIN(start_date) as week_start,
                    MAX(start_date) as week_end,
                    -- Score how "current" this week is
                    CASE 
                        -- Games happening now or very soon (highest priority)
                        WHEN COUNT(CASE WHEN start_date BETWEEN NOW() - INTERVAL '1 day' 
                                                    AND NOW() + INTERVAL '3 days' THEN 1 END) > 0 THEN 100
                        -- Games that have started but not completed (in-progress week)
                        WHEN COUNT(CASE WHEN completed = false AND start_date <= NOW() THEN 1 END) > 0 THEN 90
                        -- We're still within this week's game window
                        WHEN NOW() <= MAX(start_date) + INTERVAL '2 days' THEN 80
                        -- This week is complete, check if next week exists
                        WHEN COUNT(*) = COUNT(CASE WHEN completed = true THEN 1 END) 
                             AND NOW() > MAX(start_date) + INTERVAL '1 day' THEN 10
                        ELSE 0
                    END as current_score
                FROM games 
                WHERE season = :season 
                  AND week BETWEEN 1 AND 21
                GROUP BY week
            )
            SELECT week 
            FROM week_analysis 
            WHERE current_score > 0
            ORDER BY current_score DESC, week ASC
            LIMIT 1
        """)
        
        result = db.execute(query, {'season': season}).scalar()
        
        if result:
            return int(result)
        
        # Fallback: find the next incomplete week or last week with games
        fallback_query = text("""
            WITH weeks_with_games AS (
                SELECT 
                    week,
                    MIN(start_date) as week_start,
                    COUNT(CASE WHEN completed = false THEN 1 END) as incomplete_games
                FROM games 
                WHERE season = :season
                GROUP BY week
                ORDER BY week
            )
            SELECT week FROM weeks_with_games 
            WHERE incomplete_games > 0 
               OR week_start > NOW()
            ORDER BY week 
            LIMIT 1
        """)
        
        fallback = db.execute(fallback_query, {'season': season}).scalar()
        
        if fallback:
            return int(fallback)
        
        # Last resort: return the max week that has games
        max_week_query = text("""
            SELECT COALESCE(MAX(week), 1) 
            FROM games 
            WHERE season = :season
        """)
        
        max_week = db.execute(max_week_query, {'season': season}).scalar()
        return min(int(max_week or 1), 21)
        
    finally:
        db.close()

def get_week_label(week: int) -> str:
    """
    Get a human-readable label for a week number
    
    Args:
        week (int): Week number (1-21)
        
    Returns:
        str: Human-readable label
        
    Week mapping (matches games_load.py):
    - Weeks 1-13: Regular season
    - Week 14: Rivalry Week (Thanksgiving)
    - Week 15: Conference Championships (API regular weeks 15-16, Dec 6-7)
    - Week 16+: Bowl Season / CFP (API postseason weeks 1+, Dec 13+)
    """
    if week <= 13:
        return f'Week {week}'
    elif week == 14:
        return 'Rivalry Week'
    elif week == 15:
        return 'Conference Championships'
    elif week >= 16:
        return 'Bowl Season'
    else:
        return f'Week {week}'


def get_week_info(week, season):
    """
    Get metadata about a specific week
    REQUIRES both week and season parameters
    
    Args:
        week (int): Week number (1-20)
        season (int): Season year (e.g., 2024)
        
    Returns:
        dict: Week metadata including dates, completion status, etc.
        
    Raises:
        ValueError: If week or season is not provided
    """
    if not week or not season:
        raise ValueError("Both week and season parameters are required")
        
    db = get_db_session()
    
    try:
        query = text("""
            SELECT 
                week,
                MIN(start_date) as week_start,
                MAX(start_date) as week_end,
                COUNT(*) as total_games,
                COUNT(CASE WHEN completed = true THEN 1 END) as completed_games
            FROM games 
            WHERE season = :season AND week = :week
            GROUP BY week
        """)
        
        result = db.execute(query, {'season': season, 'week': week}).first()
        
        # Get the proper label for this week
        week_label = get_week_label(week)
        
        if not result:
            return {
                'number': week,
                'label': week_label,
                'dateRange': 'TBD',
                'isCurrent': False,
                'isComplete': False,
                'totalGames': 0,
                'completedGames': 0,
                'isPostseason': week >= 15
            }
        
        current_week = get_current_week_of_season(season)  # Pass season explicitly
        is_complete = result.completed_games == result.total_games
        
        # Format date range
        if result.week_start and result.week_end:
            if result.week_start.date() == result.week_end.date():
                date_range = result.week_start.strftime('%b %d, %Y')
            else:
                start_fmt = result.week_start.strftime('%b %d')
                end_fmt = result.week_end.strftime('%b %d, %Y')
                date_range = f'{start_fmt} - {end_fmt}'
        else:
            date_range = 'TBD'
        
        return {
            'number': week,
            'label': week_label,
            'dateRange': date_range,
            'isCurrent': week == current_week,
            'isComplete': is_complete,
            'totalGames': result.total_games,
            'completedGames': result.completed_games,
            'isPostseason': week >= 15
        }
        
    finally:
        db.close()

def get_season_weeks(season):
    """
    Get all available weeks for a season
    
    Args:
        season (int): Season year (e.g., 2024)
        
    Returns:
        list: List of week numbers that have games
    """
    if not season:
        raise ValueError("Season parameter is required")
        
    db = get_db_session()
    
    try:
        query = text("""
            SELECT DISTINCT week 
            FROM games 
            WHERE season = :season 
            ORDER BY week
        """)
        
        result = db.execute(query, {'season': season}).fetchall()
        return [row.week for row in result]
        
    finally:
        db.close()


def get_api_week_params(internal_week: int) -> list:
    """
    Map our internal week number to CFB API week number and seasonType.
    
    This is the CANONICAL mapping used by all game loaders.
    
    Internal Week Mapping:
    - Weeks 1-14: Regular season (API regular weeks 1-14)
    - Week 15: Conference Championships (API regular weeks 15-16, both Dec 6-7)
    - Week 16-21: Bowl Season / CFP (API postseason weeks 1-6)
    
    Args:
        internal_week (int): Our internal week number (1-21)
        
    Returns:
        list of tuples: [(api_week, season_type, description), ...]
        Multiple tuples returned when we need to fetch from multiple API weeks
        (e.g., Conference Championships spans API weeks 15 and 16)
    """
    if internal_week <= 14:
        # Regular season weeks 1-14
        return [(internal_week, 'regular', f'Regular season week {internal_week}')]
    
    elif internal_week == 15:
        # Conference Championships - API puts these as regular weeks 15-16
        # Need to fetch BOTH weeks from the API
        return [
            (15, 'regular', 'Conference Championships (API week 15)'),
            (16, 'regular', 'Conference Championships (API week 16)')
        ]
    
    elif internal_week >= 16:
        # Bowl games / CFP - API postseason weeks 1-6
        # Our week 16 = API postseason week 1
        # Our week 17 = API postseason week 2, etc.
        api_postseason_week = internal_week - 15
        return [(api_postseason_week, 'postseason', f'Bowl/CFP games (API postseason week {api_postseason_week})')]
    
    else:
        raise ValueError(f"Invalid internal week: {internal_week}")


def get_all_api_week_params_for_season() -> list:
    """
    Get all API week parameters needed to fetch a complete season.
    
    Returns:
        list of tuples: [(internal_week, api_week, season_type), ...]
    """
    all_params = []
    
    # Regular season weeks 1-14
    for week in range(1, 15):
        all_params.append((week, week, 'regular'))
    
    # Conference Championships (internal week 15 = API regular weeks 15+16)
    all_params.append((15, 15, 'regular'))
    all_params.append((15, 16, 'regular'))
    
    # Bowl season (internal weeks 16-21 = API postseason weeks 1-6)
    for internal_week in range(16, 22):
        api_week = internal_week - 15
        all_params.append((internal_week, api_week, 'postseason'))
    
    return all_params
