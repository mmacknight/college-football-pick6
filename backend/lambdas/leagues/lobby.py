import json
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, LeagueTeam, User
from responses import success_response, error_response, not_found_response
from auth import require_auth, get_user_id_from_event
from sqlalchemy import and_

@require_auth
def lambda_handler(event, context):
    """Get league lobby information (accessible to all league members)"""
    try:
        league_id = event['pathParameters']['id']
        user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Get league
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Check if user is a member of this league
            user_membership = db.query(LeagueTeam).filter(
                and_(LeagueTeam.league_id == league_id, LeagueTeam.user_id == user_id)
            ).first()
            
            if not user_membership:
                return error_response('You are not a member of this league', 403)
            
            # Get all league members with their details
            members_query = db.query(LeagueTeam, User)\
                .join(User, LeagueTeam.user_id == User.id)\
                .filter(LeagueTeam.league_id == league_id)\
                .order_by(LeagueTeam.joined_at)\
                .all()
            
            members = []
            for league_team, user in members_query:
                members.append({
                    'userId': str(user.id),
                    'displayName': user.display_name,
                    'teamName': league_team.team_name,
                    'draftPosition': league_team.draft_position,
                    'joinedAt': league_team.joined_at.isoformat(),
                    'isCreator': str(user.id) == str(league.created_by)
                })
            
            # Get creator info
            creator = db.query(User).filter(User.id == league.created_by).first()
            creator_name = creator.display_name if creator else 'Unknown'
            
            return success_response({
                'league': {
                    'id': str(league.id),
                    'name': league.name,
                    'season': league.season,
                    'status': league.status,
                    'joinCode': league.join_code,
                    'maxTeamsPerUser': league.max_teams_per_user,
                    'createdAt': league.created_at.isoformat(),
                    'createdBy': str(league.created_by),
                    'createdByName': creator_name
                },
                'members': members,
                'stats': {
                    'totalMembers': len(members),
                    'canStartDraft': len(members) >= 2
                },
                'userMembership': {
                    'userId': str(user_membership.user_id),
                    'teamName': user_membership.team_name,
                    'draftPosition': user_membership.draft_position,
                    'joinedAt': user_membership.joined_at.isoformat(),
                    'isCreator': str(user_id) == str(league.created_by)
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"League lobby error: {str(e)}")
        import traceback
        print(f"League lobby traceback: {traceback.format_exc()}")
        return error_response('Failed to get league lobby information', 500)
