"""
Update player team assignments (admin only)
"""

import json
from sqlalchemy import and_
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, User, School
from responses import success_response, error_response, validation_error_response, not_found_response
from auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Update a player's team assignments - only league creator can modify"""
    try:
        # Parse the league ID and user ID from path
        league_id = event.get('pathParameters', {}).get('id')
        player_user_id = event.get('pathParameters', {}).get('userId')
        
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        if not player_user_id:
            return validation_error_response({'userId': 'Player user ID is required'})
        
        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        admin_user_id = get_user_id_from_event(event)
        
        # Extract the new team assignments
        team_assignments = body.get('teamAssignments', [])
        
        # Validate team assignments structure
        for assignment in team_assignments:
            if not isinstance(assignment, dict) or 'schoolId' not in assignment:
                return validation_error_response({'teamAssignments': 'Each assignment must have schoolId'})
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            if str(league.created_by) != str(admin_user_id):
                return error_response('Only the league creator can update player teams', 403)
            
            # Verify the player exists in this league
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
            
            # Validate that all school IDs exist and are not already taken by other players
            school_ids = [assignment['schoolId'] for assignment in team_assignments]
            
            # Check if schools exist
            existing_schools = db.query(School).filter(School.id.in_(school_ids)).all()
            existing_school_ids = {school.id for school in existing_schools}
            
            missing_schools = set(school_ids) - existing_school_ids
            if missing_schools:
                return validation_error_response({
                    'teamAssignments': f'Schools not found: {list(missing_schools)}'
                })
            
            # Check for conflicts with other players (excluding the current player)
            conflicting_assignments = db.query(LeagueTeamSchoolAssignment).filter(
                and_(
                    LeagueTeamSchoolAssignment.league_id == league_id,
                    LeagueTeamSchoolAssignment.user_id != player_user_id,
                    LeagueTeamSchoolAssignment.school_id.in_(school_ids)
                )
            ).all()
            
            if conflicting_assignments:
                conflicts = [(assignment.school_id, assignment.user_id) for assignment in conflicting_assignments]
                return error_response(
                    f'Some schools are already assigned to other players: {conflicts}', 400
                )
            
            # Validate team count doesn't exceed league limit
            if len(team_assignments) > league.max_teams_per_user:
                return error_response(
                    f'Cannot assign {len(team_assignments)} teams - league limit is {league.max_teams_per_user}', 400
                )
            
            # Remove all existing assignments for this player
            db.query(LeagueTeamSchoolAssignment).filter(
                and_(
                    LeagueTeamSchoolAssignment.league_id == league_id,
                    LeagueTeamSchoolAssignment.user_id == player_user_id
                )
            ).delete()
            
            # Add new assignments
            new_assignments = []
            for i, assignment in enumerate(team_assignments):
                school_id = assignment['schoolId']
                draft_round = assignment.get('draftRound', i + 1)  # Default to sequential rounds
                draft_pick_overall = assignment.get('draftPickOverall')  # Optional
                
                new_assignment = LeagueTeamSchoolAssignment(
                    league_id=league_id,
                    user_id=player_user_id,
                    school_id=school_id,
                    draft_round=draft_round,
                    draft_pick_overall=draft_pick_overall
                )
                
                db.add(new_assignment)
                new_assignments.append({
                    'schoolId': school_id,
                    'draftRound': draft_round,
                    'draftPickOverall': draft_pick_overall
                })
            
            db.commit()
            
            # Get school details for response
            updated_schools = db.query(School).filter(School.id.in_(school_ids)).all()
            school_details = []
            for school in updated_schools:
                school_details.append({
                    'id': school.id,
                    'name': school.name,
                    'mascot': school.mascot,
                    'conference': school.conference,
                    'primaryColor': school.primary_color
                })
            
            return success_response({
                'message': f'Successfully updated {player_name}\'s team assignments',
                'player': {
                    'userId': str(player_user_id),
                    'displayName': player_name
                },
                'teamCount': len(team_assignments),
                'assignments': new_assignments,
                'schools': school_details
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Update player teams error: {str(e)}")
        import traceback
        print(f"Update player teams traceback: {traceback.format_exc()}")
        return error_response('Failed to update player teams', 500)
