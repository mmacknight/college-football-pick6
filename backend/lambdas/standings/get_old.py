import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, User, LeagueTeam, LeagueTeamSchoolAssignment, School, Game
from shared.responses import success_response, error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, text

def lambda_handler(event, context):
    """Get league standings with win calculations - PUBLIC API"""
    try:
        # Get league ID from path parameters
        league_id = event['pathParameters']['league_id']
        # No auth required for public viewing
        
        db = get_db_session()
        try:
            # Get league with members and their teams
            league = db.query(League)\
                .options(joinedload(League.league_teams).joinedload(LeagueTeam.user))\
                .options(joinedload(League.league_teams).joinedload(LeagueTeam.school_assignments).joinedload(LeagueTeamSchoolAssignment.school))\
                .filter(League.id == league_id)\
                .first()
            
            if not league:
                return not_found_response('League')
            
            # Public API - no membership check required
            
            # Get all league members first (even if they haven't drafted teams yet)
            league_members = db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id
            ).all()
            
            print(f"Debug: Found {len(league_members)} league members")
            
            members = []
            for league_team in league_members:
                user = league_team.user
                
                # Get user's drafted schools for this league
                school_assignments = db.query(LeagueTeamSchoolAssignment).filter(
                    and_(
                        LeagueTeamSchoolAssignment.league_id == league_id,
                        LeagueTeamSchoolAssignment.user_id == user.id
                    )
                ).all()
                
                print(f"Debug: User {user.display_name} has {len(school_assignments)} drafted teams")
                
                # Calculate wins for user's teams
                total_wins = 0
                total_losses = 0
                total_games = 0
                teams = []
                
                for assignment in school_assignments:
                    school = assignment.school
                    
                    # Count wins for this school
                    wins_query = db.query(Game).filter(
                        and_(
                            Game.season == league.season,
                            Game.completed == True,
                            or_(
                                and_(Game.home_id == school.id, Game.home_points > Game.away_points),
                                and_(Game.away_id == school.id, Game.away_points > Game.home_points)
                            )
                        )
                    )
                    school_wins = wins_query.count()
                    total_wins += school_wins
                    
                    # Count total completed games for this school
                    games_query = db.query(Game).filter(
                        and_(
                            Game.season == league.season,
                            Game.completed == True,
                            or_(Game.home_id == school.id, Game.away_id == school.id)
                        )
                    )
                    school_games = games_query.count()
                    school_losses = school_games - school_wins
                    total_losses += school_losses
                    total_games += school_games
                    
                    # Find current/recent game for this school
                    current_game = None
                    # Get current week or most recent game for this school
                    from shared.week_utils import get_current_week_of_season
                    current_week = get_current_week_of_season(league.season)
                    
                    # Try to get current week game first
                    recent_game = db.query(Game).filter(
                        and_(
                            Game.season == league.season,
                            Game.week == current_week,
                            or_(Game.home_id == school.id, Game.away_id == school.id)
                        )
                    ).first()
                    
                    # If no current week game, get most recent
                    if not recent_game:
                        recent_game = db.query(Game).filter(
                            and_(
                                Game.season == league.season,
                                or_(Game.home_id == school.id, Game.away_id == school.id)
                            )
                        ).order_by(Game.week.desc()).first()
                    
                    if recent_game:
                        opponent_id = recent_game.away_id if recent_game.home_id == school.id else recent_game.home_id
                        opponent = db.query(School).filter(School.id == opponent_id).first()
                        
                        # Determine game status
                        if recent_game.completed:
                            status = 'completed'
                        elif recent_game.start_date:
                            # Check if game has started - use timezone-naive comparison
                            from datetime import datetime
                            current_time = datetime.now()
                            # Make sure both are timezone-naive for comparison
                            game_start = recent_game.start_date
                            if hasattr(game_start, 'replace') and game_start.tzinfo is not None:
                                game_start = game_start.replace(tzinfo=None)
                            
                            if game_start <= current_time:
                                status = 'in_progress'
                            else:
                                status = 'scheduled'
                        else:
                            status = 'scheduled'
                        
                        current_game = {
                            'opponent': opponent.name if opponent else 'TBD',
                            'score': {
                                'home': recent_game.home_points or 0,
                                'away': recent_game.away_points or 0
                            },
                            'isHome': recent_game.home_id == school.id,
                            'status': status,
                            'week': recent_game.week,
                            'date': recent_game.start_date.strftime('%m/%d %I:%M %p') if recent_game.start_date else 'TBD'
                        }
                    
                    teams.append({
                        'id': school.id,
                        'name': school.name,
                        'mascot': school.mascot,
                        'conference': school.conference,
                        'primaryColor': school.primary_color,
                        'wins': school_wins,
                        'losses': school_games - school_wins,
                        'currentGame': current_game
                    })
                
                members.append({
                    'id': str(user.id),
                    'displayName': user.display_name,
                    'teamName': league_team.team_name,  # Add team name
                    'teams': teams,
                    'wins': total_wins,
                    'losses': total_losses,
                    'gamesPlayed': total_games // len(school_assignments) if school_assignments else 0  # Average games per team
                })
            
            # Sort by wins descending, then by display name
            members.sort(key=lambda x: (-x['wins'], x['displayName']))
            
            print(f"Debug: Returning {len(members)} members")
            
            return success_response({
                'id': str(league.id),
                'name': league.name,
                'season': league.season,
                'status': league.status,
                'createdBy': str(league.created_by),  # Add creator ID for settings access
                'members': members
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get standings error: {str(e)}")
        print(f"Get standings error type: {type(e)}")
        import traceback
        print(f"Get standings traceback: {traceback.format_exc()}")
        return error_response('Failed to get standings', 500)
