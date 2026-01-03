import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, School, User
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Get user's drafted teams for a specific league"""
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
            
            # Verify user is a member of this league
            league_team = db.query(LeagueTeam).filter(
                LeagueTeam.league_id == league_id,
                LeagueTeam.user_id == user_id
            ).first()
            if not league_team:
                return error_response('You are not a member of this league', 403)
            
            # Get user's school assignments in this league
            school_assignments = db.query(LeagueTeamSchoolAssignment, School).join(
                School, LeagueTeamSchoolAssignment.school_id == School.id
            ).filter(
                LeagueTeamSchoolAssignment.league_id == league_id,
                LeagueTeamSchoolAssignment.user_id == user_id
            ).order_by(LeagueTeamSchoolAssignment.draft_round).all()
            
            # Format response
            teams = []
            for assignment, school in school_assignments:
                teams.append({
                    'id': f"{league_id}_{user_id}_{school.id}",  # Composite identifier
                    'draftRound': assignment.draft_round,
                    'draftPickOverall': assignment.draft_pick_overall,
                    'pickedAt': assignment.drafted_at.isoformat(),
                    'school': {
                        'id': school.id,
                        'name': school.name,
                        'mascot': school.mascot,
                        'conference': school.conference,
                        'primaryColor': school.primary_color,
                        'secondaryColor': school.secondary_color,
                        'abbreviation': school.abbreviation
                    }
                })
            
            return success_response({
                'teams': teams,
                'totalTeams': len(teams),
                'maxTeams': league.max_teams_per_user,
                'spotsRemaining': league.max_teams_per_user - len(teams)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"My teams error: {str(e)}")
        print(f"My teams error type: {type(e)}")
        import traceback
        print(f"My teams traceback: {traceback.format_exc()}")
        return error_response('Failed to fetch user teams', 500)
