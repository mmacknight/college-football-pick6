import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, require_league_creator

@require_auth
def lambda_handler(event, context):
    """Skip draft and move league directly to active status for manual assignment"""
    try:
        # Get league ID from path parameters
        league_id = event.get('pathParameters', {}).get('league_id')
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        db = get_db_session()
        try:
            # Verify league exists
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Check if user is the league creator
            creator_check = require_league_creator(league, event, "skip the draft")
            if creator_check:
                return creator_check
            
            # Check league status - can only skip draft from pre_draft
            if league.status != 'pre_draft':
                return error_response(f'Cannot skip draft - league status is {league.status}', 400)
            
            # Get all teams in the league
            league_teams = db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id
            ).all()
            
            if len(league_teams) < 1:
                return error_response('Need at least 1 player to activate league', 400)
            
            # Update league status directly to active
            league.status = 'active'
            
            db.commit()
            
            return success_response({
                'message': 'League activated successfully. You can now manually assign teams to players.',
                'leagueId': str(league_id),
                'status': 'active'
            })
            
        except Exception as e:
            db.rollback()
            print(f"Database error in skip_draft: {str(e)}")
            return error_response('Failed to activate league', 500)
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error in skip_draft lambda: {str(e)}")
        return error_response('Internal server error', 500)
