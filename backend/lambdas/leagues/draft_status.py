import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, User, LeagueDraft
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event
from sqlalchemy import func

@require_auth
def lambda_handler(event, context):
    """Get the current draft status (whose turn, what pick, etc.)"""
    try:
        # Get league ID from path parameters
        league_id = event.get('pathParameters', {}).get('league_id')
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Verify league exists
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Get league teams with proper draft positions
            league_teams = db.query(LeagueTeam, User).join(
                User, LeagueTeam.user_id == User.id
            ).filter(
                LeagueTeam.league_id == league_id
            ).order_by(LeagueTeam.draft_position).all()
            
            if not league_teams:
                return error_response('No players have joined this league yet', 400)
            
            # Get total picks made so far
            total_picks_made = db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).count()
            
            total_users = len(league_teams)
            total_possible_picks = league.max_teams_per_user * total_users
            
            # Check league status and get draft state
            if league.status == 'pre_draft':
                draft_status = 'waiting'
                current_user_id = None
                current_user_name = "Draft not started"
                current_team_name = "Draft not started"
                current_pick_overall = None
                current_round = 1
                is_user_turn = False
                
            elif league.status == 'drafting':
                # Get draft state from LeagueDraft table
                draft = db.query(LeagueDraft).filter(LeagueDraft.league_id == league_id).first()
                
                if not draft:
                    return error_response('Draft state not found - league may need to be restarted', 500)
                
                current_pick_overall = draft.current_pick_overall
                
                if current_pick_overall <= total_possible_picks:
                    # Draft is active
                    draft_status = 'active'
                    current_user_id = str(draft.current_user_id) if draft.current_user_id else None
                    
                    # Get current user's display name
                    if current_user_id:
                        current_user = next((user for team, user in league_teams if str(user.id) == current_user_id), None)
                        current_user_name = current_user.display_name if current_user else "Unknown"
                        current_team_name = f"{current_user_name}'s Team"
                    else:
                        current_user_name = "Unknown"
                        current_team_name = "Unknown"
                    
                    current_round = ((current_pick_overall - 1) // total_users) + 1
                    is_user_turn = current_user_id == str(user_id) if current_user_id else False
                else:
                    # Draft is complete but status not updated
                    draft_status = 'complete'
                    current_user_id = None
                    current_user_name = None
                    current_team_name = None
                    current_round = league.max_teams_per_user
                    is_user_turn = False
                    
            elif league.status == 'active':
                draft_status = 'complete'
                current_user_id = None
                current_user_name = None
                current_team_name = None
                current_pick_overall = None
                current_round = league.max_teams_per_user
                is_user_turn = False
                
            else:
                draft_status = 'unknown'
                current_user_id = None
                current_user_name = f"League status: {league.status}"
                current_team_name = None
                current_pick_overall = None
                current_round = 1
                is_user_turn = False
            
            # Build draft order information
            draft_order = []
            for team, user in league_teams:
                draft_order.append({
                    'draftPosition': team.draft_position or 0,
                    'userId': str(user.id),
                    'displayName': user.display_name,
                    'teamName': team.team_name
                })
            
            return success_response({
                'currentPickOverall': current_pick_overall,
                'currentRound': current_round,
                'currentUserId': current_user_id,
                'currentUserName': current_user_name,
                'currentTeamName': current_team_name,
                'isUserTurn': is_user_turn,
                'totalPicks': total_possible_picks,
                'picksMade': total_picks_made,
                'picksRemaining': max(0, total_possible_picks - total_picks_made),
                'totalUsers': total_users,
                'draftStatus': draft_status,  # 'waiting', 'active', 'complete', 'unknown'
                'leagueStatus': league.status,
                'draftOrder': draft_order,
                'leagueInfo': {
                    'id': str(league.id),
                    'name': league.name,
                    'maxTeamsPerUser': league.max_teams_per_user,
                    'status': league.status
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Draft status error: {str(e)}")
        print(f"Draft status error type: {type(e)}")
        import traceback
        print(f"Draft status traceback: {traceback.format_exc()}")
        return error_response('Failed to fetch draft status', 500)
