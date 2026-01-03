"""
Add manual team to league (commissioner only)
Creates a dummy user account to maintain database integrity
"""

import json
import uuid
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, User
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event, hash_password
from sqlalchemy.exc import IntegrityError

@require_auth
def lambda_handler(event, context):
    """Add a manual team to a league - only league creator can do this"""
    try:
        # Parse the league ID from path
        league_id = event.get('pathParameters', {}).get('league_id')
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        user_id = get_user_id_from_event(event)
        
        # Extract team details
        player_name = body.get('playerName', '').strip()
        team_name = body.get('teamName', '').strip()
        
        # Validate inputs
        errors = {}
        if not player_name:
            errors['playerName'] = 'Player name is required'
        elif len(player_name) < 2:
            errors['playerName'] = 'Player name must be at least 2 characters'
        elif len(player_name) > 50:
            errors['playerName'] = 'Player name must be less than 50 characters'
            
        if not team_name:
            errors['teamName'] = 'Team name is required'
        elif len(team_name) < 3:
            errors['teamName'] = 'Team name must be at least 3 characters'
        elif len(team_name) > 50:
            errors['teamName'] = 'Team name must be less than 50 characters'
            
        if errors:
            return validation_error_response(errors)
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            if str(league.created_by) != str(user_id):
                return error_response('Only the league creator can add manual teams', 403)
            
            # Check if league can be modified (only pre_draft leagues)
            if league.status not in ['pre_draft']:
                return error_response('Cannot add manual teams after draft has started', 400)
            
            # Count existing teams in league
            existing_teams_count = db.query(LeagueTeam).filter(LeagueTeam.league_id == league_id).count()
            
            # For now, limit to 20 teams max per league (can be made configurable)
            max_teams_in_league = 20
            if existing_teams_count >= max_teams_in_league:
                return error_response(f'League already has maximum number of teams ({max_teams_in_league})', 400)
            
            # Generate unique dummy email
            dummy_email = f"dummy-{league_id}-{uuid.uuid4().hex[:8]}@cfbpick6.internal"
            
            # Create dummy user account
            dummy_user = User(
                email=dummy_email,
                password_hash=hash_password('dummy_password_' + uuid.uuid4().hex[:16]),  # Random password
                display_name=player_name  # Use the player name as display name
            )
            
            db.add(dummy_user)
            db.flush()  # Get the ID without committing
            
            # Create league team membership for the dummy user
            new_team = LeagueTeam(
                league_id=league.id,
                user_id=dummy_user.id,
                team_name=team_name,
                draft_position=None  # Will be set when draft starts
            )
            
            db.add(new_team)
            db.commit()
            db.refresh(dummy_user)
            db.refresh(new_team)
            
            # Return the created team info
            return success_response({
                'team': {
                    'userId': str(dummy_user.id),
                    'displayName': dummy_user.display_name,
                    'teamName': new_team.team_name,
                    'draftPosition': new_team.draft_position,
                    'joinedAt': new_team.joined_at.isoformat(),
                    'isManualTeam': True,  # Flag to identify manual teams
                    'pickCount': 0,
                    'teams': []
                },
                'message': f'Added manual team "{team_name}" for player "{player_name}"'
            }, 201)
            
        except IntegrityError as e:
            db.rollback()
            print(f"Database integrity error: {str(e)}")
            return error_response('Failed to create team due to database constraint', 500)
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Add manual team error: {str(e)}")
        import traceback
        print(f"Add manual team traceback: {traceback.format_exc()}")
        return error_response('Failed to add manual team', 500)
