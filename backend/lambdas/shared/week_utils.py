"""
Week detection and management utilities for college football seasons
"""
from datetime import datetime, timedelta
from database import get_db_session, Game
from sqlalchemy import text

def get_current_week_of_season(season):
    """
    Dynamically determine the current week based on game data
    REQUIRES season parameter - no defaults
    
    Args:
        season (int): The season year (e.g., 2024)
        
    Returns:
        int: Current week number (1-17)
        
    Raises:
        ValueError: If season is not provided
    """
    if not season:
        raise ValueError("Season parameter is required")
    
    db = get_db_session()
    
    try:
        # Complex query to find the "current" week for the specific season
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
                        WHEN COUNT(CASE WHEN start_date BETWEEN NOW() - INTERVAL '1 day' 
                                                    AND NOW() + INTERVAL '3 days' THEN 1 END) > 0 THEN 100
                        WHEN COUNT(CASE WHEN completed = false AND start_date <= NOW() THEN 1 END) > 0 THEN 90
                        WHEN NOW() <= MAX(start_date) + INTERVAL '2 days' THEN 80
                        ELSE 0
                    END as current_score
                FROM games 
                WHERE season = :season 
                  AND week BETWEEN 1 AND 17
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
        
        # Fallback: find latest week with any games for this season
        fallback_query = text("""
            SELECT COALESCE(MAX(week), 1) 
            FROM games 
            WHERE season = :season
        """)
        
        fallback = db.execute(fallback_query, {'season': season}).scalar()
        return min(int(fallback or 1), 17)
        
    finally:
        db.close()

def get_week_info(week, season):
    """
    Get metadata about a specific week
    REQUIRES both week and season parameters
    
    Args:
        week (int): Week number (1-17)
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
        
        if not result:
            return {
                'number': week,
                'label': f'Week {week}',
                'dateRange': 'TBD',
                'isCurrent': False,
                'isComplete': False,
                'totalGames': 0,
                'completedGames': 0
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
            'label': f'Week {week}',
            'dateRange': date_range,
            'isCurrent': week == current_week,
            'isComplete': is_complete,
            'totalGames': result.total_games,
            'completedGames': result.completed_games
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
