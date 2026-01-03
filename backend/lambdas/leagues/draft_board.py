import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, School, User
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Get the complete draft board (all picks) for a league"""
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
            
            # Get all draft picks in this league with user and school details
            draft_picks = db.query(LeagueTeamSchoolAssignment, User, School).join(
                User, LeagueTeamSchoolAssignment.user_id == User.id
            ).join(
                School, LeagueTeamSchoolAssignment.school_id == School.id
            ).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).order_by(LeagueTeamSchoolAssignment.draft_pick_overall).all()
            
            # Format response
            picks = []
            for assignment, user, school in draft_picks:
                picks.append({
                    'id': f"{league_id}_{user.id}_{school.id}",  # Composite identifier
                    'pickNumber': assignment.draft_pick_overall,
                    'round': assignment.draft_round,
                    'teamName': f"{user.display_name}'s Team",  # Could be customizable later
                    'userName': user.display_name,
                    'userId': str(user.id),
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
            
            # Calculate draft stats
            total_possible_picks = league.max_teams_per_user * 4  # Assuming 4 users for now
            picks_made = len(picks)
            current_round = ((picks_made) // league.max_teams_per_user) + 1 if picks_made < total_possible_picks else league.max_teams_per_user
            
            return success_response({
                'picks': picks,
                'totalPicks': picks_made,
                'totalPossiblePicks': total_possible_picks,
                'currentRound': current_round,
                'isComplete': picks_made >= total_possible_picks,
                'leagueInfo': {
                    'id': str(league.id),
                    'name': league.name,
                    'maxTeamsPerUser': league.max_teams_per_user
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Draft board error: {str(e)}")
        print(f"Draft board error type: {type(e)}")
        import traceback
        print(f"Draft board traceback: {traceback.format_exc()}")
        return error_response('Failed to fetch draft board', 500)
