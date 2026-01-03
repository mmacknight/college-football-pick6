import json
import sys
import os
import random
import string

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, User
from shared.responses import success_response, error_response, validation_error_response
from shared.auth import require_auth, get_user_id_from_event

def generate_join_code():
    """Generate a random 8-character join code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

@require_auth
def lambda_handler(event, context):
    """Create a new league"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        name = body.get('name', '').strip()
        season = body.get('season', 2025)
        team_name = body.get('teamName', '').strip()
        user_id = get_user_id_from_event(event)
        
        # Validate input
        errors = {}
        if not name:
            errors['name'] = 'League name is required'
        elif len(name) < 3:
            errors['name'] = 'League name must be at least 3 characters'
        elif len(name) > 50:
            errors['name'] = 'League name must be less than 50 characters'
            
        if not team_name:
            errors['teamName'] = 'Team name is required'
        elif len(team_name) < 3:
            errors['teamName'] = 'Team name must be at least 3 characters'
        elif len(team_name) > 50:
            errors['teamName'] = 'Team name must be less than 50 characters'
            
        # Convert season to int if it's a string, then validate
        if not season:
            errors['season'] = 'Season is required'
        else:
            try:
                # Convert string to int if needed
                if isinstance(season, str):
                    season = int(season)
                
                # Validate range - only allow 2025
                if not isinstance(season, int) or season != 2025:
                    errors['season'] = 'Season must be 2025'
            except (ValueError, TypeError):
                errors['season'] = 'Season must be 2025'
        
        if errors:
            return validation_error_response(errors)
        
        # Database operations
        db = get_db_session()
        try:
            # Generate unique join code
            join_code = generate_join_code()
            while db.query(League).filter(League.join_code == join_code).first():
                join_code = generate_join_code()
            
            # Create league
            new_league = League(
                name=name,
                season=season,
                join_code=join_code,
                created_by=user_id,
                status='pre_draft'
            )
            
            db.add(new_league)
            db.commit()
            db.refresh(new_league)
            
            # Create league team for the creator
            creator_team = LeagueTeam(
                league_id=new_league.id,
                user_id=user_id,
                team_name=team_name,
                draft_position=None  # Will be set when draft starts
            )
            
            db.add(creator_team)
            db.commit()
            db.refresh(creator_team)
            
            # Get creator user info for response
            creator_user = db.query(User).filter(User.id == user_id).first()
            
            return success_response({
                'id': str(new_league.id),
                'name': new_league.name,
                'season': new_league.season,
                'joinCode': new_league.join_code,
                'status': new_league.status,
                'memberCount': 1,
                'userTeamCount': 1,
                'maxTeamsPerUser': new_league.max_teams_per_user,
                'createdAt': new_league.created_at.isoformat(),
                'isCreator': True
            }, 201)
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Create league error: {str(e)}")
        print(f"Create league error type: {type(e)}")
        import traceback
        print(f"Create league traceback: {traceback.format_exc()}")
        return error_response('Failed to create league', 500)
