import json
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, User, LeagueTeam, LeagueTeamSchoolAssignment, School, Game
from responses import success_response, error_response, not_found_response
from auth import require_auth, get_user_uuid_from_event
from week_utils import get_current_week_of_season, get_week_info
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, text

@require_auth
def lambda_handler(event, context):
    """Get league games for a specific week with member team performance"""
    try:
        # Get parameters
        league_id = event['pathParameters']['league_id']
        week_param = event['pathParameters'].get('week', 'current')
        user_id = get_user_uuid_from_event(event)
        
        db = get_db_session()
        try:
            # Get league first to get the season
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Check if user is a member of this league
            user_teams = db.query(LeagueTeam).filter(
                and_(LeagueTeam.league_id == league_id, LeagueTeam.user_id == user_id)
            ).first()
            
            if not user_teams:
                return error_response('You are not a member of this league', 403)
            
            # Use the league's season - no defaults!
            season = league.season
            if not season:
                return error_response('League season not configured', 400)
            
            # Determine which week to show
            if week_param == 'current':
                week = get_current_week_of_season(season)
            else:
                try:
                    week = int(week_param)
                except ValueError:
                    return error_response('Invalid week parameter', 400)
            
            # Validate week range
            if week < 1 or week > 17:
                return error_response('Week must be between 1 and 17', 400)
            
            # Get week metadata
            week_info = get_week_info(week, season)
            
            # Check if season has games in database
            games_exist = db.query(Game).filter(Game.season == season).first()
            if not games_exist:
                return error_response(f'No game data available for {season} season', 404)
            
            # Get all league members and their teams
            league_members = db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id
            ).all()
            
            print(f"Debug: Found {len(league_members)} league members for week {week}")
            
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
                
                # Track week performance
                week_wins = 0
                week_losses = 0
                week_no_games = 0
                teams = []
                
                for assignment in school_assignments:
                    school = assignment.school
                    
                    # Find game for this school in this specific week
                    game = db.query(Game).filter(
                        and_(
                            Game.season == season,
                            Game.week == week,
                            or_(Game.home_id == school.id, Game.away_id == school.id)
                        )
                    ).first()
                    
                    if not game:
                        # No game this week
                        week_no_games += 1
                        teams.append({
                            'id': school.id,
                            'name': school.name,
                            'mascot': school.mascot,
                            'conference': school.conference,
                            'primaryColor': school.primary_color,
                            'game': None
                        })
                    else:
                        # Determine if this school won or lost
                        is_home = game.home_id == school.id
                        school_points = game.home_points if is_home else game.away_points
                        opponent_points = game.away_points if is_home else game.home_points
                        
                        # Determine result
                        if not game.completed:
                            result = 'S'  # Scheduled/In Progress
                        elif school_points > opponent_points:
                            result = 'W'
                            week_wins += 1
                        elif school_points < opponent_points:
                            result = 'L'
                            week_losses += 1
                        else:
                            result = 'T'  # Tie
                        
                        # Get opponent info
                        opponent_id = game.away_id if is_home else game.home_id
                        opponent = db.query(School).filter(School.id == opponent_id).first()
                        
                        # Format score
                        if game.completed and school_points is not None and opponent_points is not None:
                            score = f"{school_points}-{opponent_points}"
                        elif not game.completed and school_points is not None and opponent_points is not None:
                            # Live game with current score
                            score = f"{school_points}-{opponent_points}"
                        else:
                            score = "TBD"
                        
                        # Determine game status with better logic
                        from datetime import datetime, timezone
                        current_time = db.execute(text("SELECT NOW()")).scalar()
                        
                        # Handle timezone comparison issue
                        if game.start_date and current_time:
                            # Make start_date timezone-aware if it's naive
                            if game.start_date.tzinfo is None:
                                game_start_utc = game.start_date.replace(tzinfo=timezone.utc)
                            else:
                                game_start_utc = game.start_date
                            
                            # Make current_time timezone-naive for comparison if needed
                            if current_time.tzinfo is not None and game.start_date.tzinfo is None:
                                current_time_naive = current_time.replace(tzinfo=None)
                                is_started = game.start_date <= current_time_naive
                            elif current_time.tzinfo is None and game.start_date.tzinfo is not None:
                                current_time_aware = current_time.replace(tzinfo=timezone.utc)
                                is_started = game_start_utc <= current_time_aware
                            else:
                                is_started = game.start_date <= current_time
                        else:
                            is_started = False
                        
                        if game.completed:
                            status = 'completed'
                        elif is_started:
                            status = 'in_progress'
                        else:
                            status = 'scheduled'
                        
                        # Debug logging for start_date
                        print(f"Debug: Game {game.id} start_date: {game.start_date}")
                        
                        # Extract quarter info if available (mock for now - would come from live data)
                        quarter = None
                        time_remaining = None
                        if status == 'in_progress':
                            # In a real implementation, this would come from the CollegeFootballData API
                            # For now, we'll estimate based on score progression
                            total_points = (school_points or 0) + (opponent_points or 0)
                            if total_points < 14:
                                quarter = 1
                                time_remaining = "12:30"
                            elif total_points < 28:
                                quarter = 2
                                time_remaining = "8:45"
                            elif total_points < 42:
                                quarter = 3
                                time_remaining = "5:15"
                            else:
                                quarter = 4
                                time_remaining = "2:30"
                        
                        teams.append({
                            'id': school.id,
                            'name': school.name,
                            'mascot': school.mascot,
                            'conference': school.conference,
                            'primaryColor': school.primary_color,
                            'game': {
                                'opponent': opponent.name if opponent else 'TBD',
                                'opponentColor': opponent.primary_color if opponent else '#6c757d',
                                'result': result,
                                'score': score,
                                'isHome': is_home,
                                'status': status,
                                'quarter': quarter,
                                'timeRemaining': time_remaining,
                                'startDate': game.start_date.isoformat() if game.start_date else None,
                                'date': game.start_date.strftime('%m/%d %I:%M %p') if game.start_date else None
                            }
                        })
                
                # Format week record
                if week_no_games == len(school_assignments):
                    week_record = "No games"
                else:
                    week_record = f"{week_wins}-{week_losses}"
                    if week_no_games > 0:
                        week_record += f" ({week_no_games} bye)"
                
                members.append({
                    'id': str(user.id),
                    'displayName': user.display_name,
                    'weekRecord': week_record,
                    'weekWins': week_wins,
                    'weekLosses': week_losses,
                    'weekNoGames': week_no_games,
                    'teams': teams
                })
            
            # Sort by week wins descending, then by display name
            members.sort(key=lambda x: (-x['weekWins'], x['displayName']))
            
            print(f"Debug: Returning {len(members)} members for week {week}")
            
            return success_response({
                'leagueId': str(league.id),
                'leagueName': league.name,
                'season': season,
                'week': week_info,
                'members': members
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get games week error: {str(e)}")
        print(f"Get games week error type: {type(e)}")
        import traceback
        print(f"Get games week traceback: {traceback.format_exc()}")
        return error_response('Failed to get week games', 500)
