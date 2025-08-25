"""
Update league settings (admin only)
"""

import json
from sqlalchemy import and_
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment
from responses import success_response, error_response, validation_error_response, not_found_response
from auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Update league settings - only league creator can modify"""
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
        
        # Extract update fields
        name = body.get('name')
        max_teams_per_user = body.get('maxTeamsPerUser')
        
        # Validate inputs
        if name is not None and (not isinstance(name, str) or len(name.strip()) == 0):
            return validation_error_response({'name': 'League name cannot be empty'})
        
        if max_teams_per_user is not None:
            if not isinstance(max_teams_per_user, int) or max_teams_per_user < 1 or max_teams_per_user > 10:
                return validation_error_response({'maxTeamsPerUser': 'Must be between 1 and 10'})
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            if str(league.created_by) != str(user_id):
                return error_response('Only the league creator can update settings', 403)
            
            # Check if league can be modified (only pre_draft leagues)
            if league.status not in ['pre_draft']:
                return error_response('Cannot modify league settings after draft has started', 400)
            
            # Apply updates
            updated_fields = {}
            
            if name is not None:
                league.name = name.strip()
                updated_fields['name'] = league.name
            
            if max_teams_per_user is not None:
                # Check if reducing max teams would invalidate existing picks
                if max_teams_per_user < league.max_teams_per_user:
                    # Count existing picks per user
                    max_existing_picks = db.query(LeagueTeamSchoolAssignment.user_id)\
                        .filter(LeagueTeamSchoolAssignment.league_id == league_id)\
                        .group_by(LeagueTeamSchoolAssignment.user_id)\
                        .count()
                    
                    if max_existing_picks > max_teams_per_user:
                        return error_response(f'Cannot reduce max teams - some players already have {max_existing_picks} teams', 400)
                
                league.max_teams_per_user = max_teams_per_user
                updated_fields['maxTeamsPerUser'] = league.max_teams_per_user
            
            db.commit()
            
            return success_response({
                'id': str(league.id),
                'name': league.name,
                'season': league.season,
                'maxTeamsPerUser': league.max_teams_per_user,
                'status': league.status,
                'joinCode': league.join_code,
                'updatedFields': updated_fields
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Update league settings error: {str(e)}")
        import traceback
        print(f"Update league settings traceback: {traceback.format_exc()}")
        return error_response('Failed to update league settings', 500)
