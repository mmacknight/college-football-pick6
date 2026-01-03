"""
Get league ID by join code (public, no auth required)
Simple lookup to enable viewing league standings
"""

import json
from shared.database import get_db_session, League
from shared.responses import success_response, error_response, validation_error_response, not_found_response

def lambda_handler(event, context):
    """Get league ID from join code - no auth required"""
    try:
        # Parse the join code from path
        join_code = event.get('pathParameters', {}).get('join_code')
        
        if not join_code:
            return validation_error_response({'joinCode': 'Join code is required'})
        
        join_code = join_code.upper()
        
        db = get_db_session()
        
        try:
            # Look up the league
            league = db.query(League).filter(League.join_code == join_code).first()
            
            if not league:
                return not_found_response('League not found with that join code')
            
            return success_response({
                'leagueId': str(league.id),
                'name': league.name
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"View league by code error: {str(e)}")
        import traceback
        print(f"View league by code traceback: {traceback.format_exc()}")
        return error_response('Failed to load league information', 500)
