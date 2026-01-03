"""
Reset league draft state (admin only)
"""

import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, LeagueDraft
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Reset draft state - remove all picks and return league to pre_draft status"""
    try:
        # Parse the league ID from path
        league_id = event.get('pathParameters', {}).get('league_id')
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            if str(league.created_by) != str(user_id):
                return error_response('Only the league creator can reset the draft', 403)
            
            # Can only reset if league is in drafting or completed state
            if league.status not in ['drafting', 'active', 'completed']:
                return error_response(f'Cannot reset draft - league status is {league.status}', 400)
            
            # Count existing picks before deletion
            picks_count = db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).count()
            
            # Remove all draft picks
            db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).delete()
            
            # Remove draft state
            db.query(LeagueDraft).filter(
                LeagueDraft.league_id == league_id
            ).delete()
            
            # Reset all draft positions
            db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id
            ).update({'draft_position': None})
            
            # Reset league status to pre_draft
            league.status = 'pre_draft'
            
            db.commit()
            
            return success_response({
                'message': f'Successfully reset draft - removed {picks_count} picks',
                'leagueId': str(league_id),
                'leagueStatus': league.status,
                'picksRemoved': picks_count
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Reset draft error: {str(e)}")
        import traceback
        print(f"Reset draft traceback: {traceback.format_exc()}")
        return error_response('Failed to reset draft', 500)
