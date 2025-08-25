"""
Update team name for a user in a league
"""

import json
from sqlalchemy import and_
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, LeagueTeam, User
from responses import success_response, error_response, validation_error_response, not_found_response
from auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Update a user's team name in a league"""
    try:
        # Parse the league ID from path
        league_id = event.get('pathParameters', {}).get('id')
        
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        user_id = get_user_id_from_event(event)
        
        # Extract the new team name
        team_name = body.get('teamName', '').strip()
        
        # Validate team name
        if not team_name:
            return validation_error_response({'teamName': 'Team name is required'})
        if len(team_name) < 3:
            return validation_error_response({'teamName': 'Team name must be at least 3 characters'})
        if len(team_name) > 50:
            return validation_error_response({'teamName': 'Team name must be less than 50 characters'})
        
        db = get_db_session()
        try:
            # Verify league exists
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Verify the user is a member of this league
            league_team = db.query(LeagueTeam).filter(
                and_(
                    LeagueTeam.league_id == league_id,
                    LeagueTeam.user_id == user_id
                )
            ).first()
            
            if not league_team:
                return not_found_response('You are not a member of this league')
            
            # Update the team name
            league_team.team_name = team_name
            db.commit()
            
            # Get user info for response
            user = db.query(User).filter(User.id == user_id).first()
            
            return success_response({
                'message': 'Team name updated successfully',
                'teamName': team_name,
                'user': {
                    'id': str(user.id),
                    'displayName': user.display_name
                }
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Update team name error: {str(e)}")
        import traceback
        print(f"Update team name traceback: {traceback.format_exc()}")
        return error_response('Failed to update team name', 500)
