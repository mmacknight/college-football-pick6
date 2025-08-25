"""
Remove a player from a league (admin only)
"""

import json
from sqlalchemy import and_
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, LeagueDraft, User
from responses import success_response, error_response, validation_error_response, not_found_response
from auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Remove a player from a league - only league creator can do this"""
    try:
        # Parse the league ID and user ID from path
        league_id = event.get('pathParameters', {}).get('id')
        player_user_id = event.get('pathParameters', {}).get('userId')
        
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        if not player_user_id:
            return validation_error_response({'userId': 'Player user ID is required'})
        
        admin_user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            if str(league.created_by) != str(admin_user_id):
                return error_response('Only the league creator can remove players', 403)
            
            # Check if league can be modified
            if league.status not in ['pre_draft', 'drafting']:
                return error_response('Cannot remove players from active or completed leagues', 400)
            
            # Prevent league creator from removing themselves
            if str(admin_user_id) == str(player_user_id):
                return error_response('League creator cannot remove themselves', 400)
            
            # Find the player's league team
            league_team = db.query(LeagueTeam).filter(
                and_(
                    LeagueTeam.league_id == league_id,
                    LeagueTeam.user_id == player_user_id
                )
            ).first()
            
            if not league_team:
                return not_found_response('Player not found in this league')
            
            # Get player info for response
            player = db.query(User).filter(User.id == player_user_id).first()
            player_name = player.display_name if player else "Unknown Player"
            
            # Remove all of the player's draft picks
            db.query(LeagueTeamSchoolAssignment).filter(
                and_(
                    LeagueTeamSchoolAssignment.league_id == league_id,
                    LeagueTeamSchoolAssignment.user_id == player_user_id
                )
            ).delete()
            
            # Remove the league team membership
            db.delete(league_team)
            
            # If league is currently drafting, update draft state
            if league.status == 'drafting':
                draft = db.query(LeagueDraft).filter(LeagueDraft.league_id == league_id).first()
                if draft:
                    # If it was the removed player's turn, advance to next player
                    if draft.current_user_id == player_user_id:
                        # Get remaining players in draft order
                        remaining_teams = db.query(LeagueTeam).filter(
                            LeagueTeam.league_id == league_id
                        ).order_by(LeagueTeam.draft_position).all()
                        
                        if remaining_teams:
                            # Calculate who should pick next
                            current_pick = draft.current_pick_overall
                            total_remaining = len(remaining_teams)
                            max_teams = league.max_teams_per_user
                            
                            # Simple round-robin for now (can be made snake later)
                            next_player_index = (current_pick - 1) % total_remaining
                            next_player = remaining_teams[next_player_index]
                            
                            draft.current_user_id = next_player.user_id
                        else:
                            # No players left, end draft
                            league.status = 'active'
                            draft.current_user_id = None
                    
                    # Recalculate total picks
                    remaining_count = db.query(LeagueTeam).filter(
                        LeagueTeam.league_id == league_id
                    ).count()
                    draft.total_picks = remaining_count * league.max_teams_per_user
            
            db.commit()
            
            return success_response({
                'message': f'Successfully removed {player_name} from the league',
                'removedPlayer': {
                    'userId': str(player_user_id),
                    'displayName': player_name
                },
                'leagueStatus': league.status
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Remove player error: {str(e)}")
        import traceback
        print(f"Remove player traceback: {traceback.format_exc()}")
        return error_response('Failed to remove player', 500)
