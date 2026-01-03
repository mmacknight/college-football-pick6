import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, User, School
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event
from sqlalchemy import and_

@require_auth
def lambda_handler(event, context):
    """Join a league by join code"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        join_code = body.get('joinCode', '').strip().upper()
        team_name = body.get('teamName', '').strip()
        user_id = get_user_id_from_event(event)
        
        # Validate input
        errors = {}
        if not join_code:
            errors['joinCode'] = 'Join code is required'
        elif len(join_code) != 8:
            errors['joinCode'] = 'Join code must be 8 characters'
            
        if not team_name:
            errors['teamName'] = 'Team name is required'
        elif len(team_name) < 3:
            errors['teamName'] = 'Team name must be at least 3 characters'
        elif len(team_name) > 50:
            errors['teamName'] = 'Team name must be less than 50 characters'
            
        if errors:
            return validation_error_response(errors)
        
        # Database operations
        db = get_db_session()
        try:
            # Find league by join code
            league = db.query(League).filter(League.join_code == join_code).first()
            
            if not league:
                return not_found_response('League with that join code')
            
            # Check if user is already a member
            existing_membership = db.query(LeagueTeam).filter(
                and_(LeagueTeam.league_id == league.id, LeagueTeam.user_id == user_id)
            ).first()
            
            if existing_membership:
                return error_response('You are already a member of this league', 409)
            
            # Check league status - only allow joining pre_draft and drafting leagues
            if league.status not in ['pre_draft', 'drafting']:
                return error_response('This league is no longer accepting new members', 400)
            
            # Create league team membership
            new_team = LeagueTeam(
                league_id=league.id,
                user_id=user_id,
                team_name=team_name,
                draft_position=None  # Will be set when draft starts
            )
            
            db.add(new_team)
            db.commit()
            db.refresh(new_team)
            
            # Get current members for the response
            members_query = db.query(LeagueTeam, User)\
                .join(User, LeagueTeam.user_id == User.id)\
                .filter(LeagueTeam.league_id == league.id)\
                .order_by(LeagueTeam.joined_at)\
                .all()
            
            members = []
            for league_team, user in members_query:
                members.append({
                    'userId': str(user.id),
                    'displayName': user.display_name,
                    'teamName': league_team.team_name,
                    'draftPosition': league_team.draft_position,
                    'joinedAt': league_team.joined_at.isoformat()
                })
            
            return success_response({
                'id': str(league.id),
                'name': league.name,
                'season': league.season,
                'status': league.status,
                'joinCode': league.join_code,
                'createdAt': league.created_at.isoformat(),
                'maxTeamsPerUser': league.max_teams_per_user,
                'members': members,
                'userTeam': {
                    'leagueId': str(new_team.league_id),
                    'userId': str(new_team.user_id),
                    'teamName': new_team.team_name,
                    'draftPosition': new_team.draft_position
                }
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Join league error: {str(e)}")
        return error_response('Failed to join league', 500)
