import json
import sys
import os
import random

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueDraft, User
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, require_league_creator
from sqlalchemy import and_, func

@require_auth
def lambda_handler(event, context):
    """Start the draft for a league - randomize draft order and begin drafting"""
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
            
            # Check if user is the league creator (using centralized auth utility)
            creator_check = require_league_creator(league, event, "start the draft")
            if creator_check:
                return creator_check
            
            # Check league status - can only start draft from pre_draft
            if league.status != 'pre_draft':
                return error_response(f'Cannot start draft - league status is {league.status}', 400)
            
            # Get all teams in the league
            league_teams = db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id
            ).all()
            
            if len(league_teams) < 2:
                return error_response('Need at least 2 players to start draft', 400)
            
            # Check if draft already exists
            existing_draft = db.query(LeagueDraft).filter(
                LeagueDraft.league_id == league_id
            ).first()
            
            if existing_draft:
                return error_response('Draft has already been started for this league', 409)
            
            # Randomize draft order
            teams_list = list(league_teams)
            random.shuffle(teams_list)
            
            # Update draft positions
            for i, team in enumerate(teams_list):
                team.draft_position = i + 1
            
            # Calculate total picks
            total_picks = len(teams_list) * league.max_teams_per_user
            
            # Create draft record
            draft = LeagueDraft(
                league_id=league_id,
                current_pick_overall=1,
                current_league_id=league_id,
                current_user_id=teams_list[0].user_id,  # First picker
                total_picks=total_picks,
                started_at=func.now()
            )
            
            # Update league status to drafting
            league.status = 'drafting'
            
            db.add(draft)
            db.commit()
            
            # Get updated team info with user details for response
            teams_with_users = db.query(LeagueTeam, User).join(
                User, LeagueTeam.user_id == User.id
            ).filter(
                LeagueTeam.league_id == league_id
            ).order_by(LeagueTeam.draft_position).all()
            
            draft_order = []
            for team, user in teams_with_users:
                draft_order.append({
                    'draftPosition': team.draft_position,
                    'userId': str(user.id),
                    'displayName': user.display_name,
                    'teamName': team.team_name
                })
            
            return success_response({
                'draftStarted': True,
                'draftOrder': draft_order,
                'currentPicker': {
                    'userId': str(teams_list[0].user_id),
                    'pickNumber': 1,
                    'totalPicks': total_picks
                },
                'leagueStatus': 'drafting'
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Start draft error: {str(e)}")
        print(f"Start draft error type: {type(e)}")
        import traceback
        print(f"Start draft traceback: {traceback.format_exc()}")
        return error_response('Failed to start draft', 500)
