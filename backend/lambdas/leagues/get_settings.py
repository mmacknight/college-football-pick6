"""
Get league settings and member list (admin only)
"""

import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, LeagueTeamSchoolAssignment, User, School
from shared.responses import success_response, error_response, validation_error_response, not_found_response
from shared.auth import require_auth, get_user_id_from_event

@require_auth
def lambda_handler(event, context):
    """Get league settings and member list - only league creator can access"""
    try:
        # Parse the league ID from path
        league_id = event.get('pathParameters', {}).get('league_id')
        if not league_id:
            return validation_error_response({'id': 'League ID is required'})
        
        user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Verify league exists and user is creator
            league = db.query(League).filter(League.id == league_id).first()
            if not league:
                return not_found_response('League')
            
            # Debug logging
            print(f"DEBUG: user_id from token: {user_id} (type: {type(user_id)})")
            print(f"DEBUG: league.created_by: {league.created_by} (type: {type(league.created_by)})")
            print(f"DEBUG: user_id == league.created_by: {user_id == league.created_by}")
            print(f"DEBUG: str(user_id) == str(league.created_by): {str(user_id) == str(league.created_by)}")
            
            if str(league.created_by) != str(user_id):
                return error_response('Only the league creator can access settings', 403)
            
            # Get creator info
            creator = db.query(User).filter(User.id == league.created_by).first()
            
            # Get all members with their pick counts and teams
            members_query = db.query(LeagueTeam, User)\
                .join(User, LeagueTeam.user_id == User.id)\
                .filter(LeagueTeam.league_id == league_id)\
                .order_by(LeagueTeam.joined_at)\
                .all()
            
            members = []
            for league_team, user in members_query:
                # Get all teams (schools) for this user
                teams_query = db.query(LeagueTeamSchoolAssignment, School)\
                    .join(School, LeagueTeamSchoolAssignment.school_id == School.id)\
                    .filter(
                        LeagueTeamSchoolAssignment.league_id == league_id,
                        LeagueTeamSchoolAssignment.user_id == user.id
                    )\
                    .order_by(LeagueTeamSchoolAssignment.draft_round)\
                    .all()
                
                teams = []
                for assignment, school in teams_query:
                    teams.append({
                        'id': school.id,
                        'name': school.name,
                        'mascot': school.mascot,
                        'conference': school.conference,
                        'primaryColor': school.primary_color,
                        'draftRound': assignment.draft_round,
                        'draftPickOverall': assignment.draft_pick_overall
                    })
                
                # Check if this is a manual team (dummy user)
                is_manual_team = user.email.endswith('@cfbpick6.internal')
                
                members.append({
                    'userId': str(user.id),
                    'displayName': user.display_name,
                    'teamName': league_team.team_name,
                    'draftPosition': league_team.draft_position,
                    'joinedAt': league_team.joined_at.isoformat(),
                    'pickCount': len(teams),
                    'teams': teams,  # Add the actual teams
                    'isCreator': user.id == league.created_by,
                    'isManualTeam': is_manual_team  # Flag to identify manual teams
                })
            
            # Count total picks made
            total_picks = db.query(LeagueTeamSchoolAssignment).filter(
                LeagueTeamSchoolAssignment.league_id == league_id
            ).count()
            
            return success_response({
                'league': {
                    'id': str(league.id),
                    'name': league.name,
                    'season': league.season,
                    'status': league.status,
                    'joinCode': league.join_code,
                    'maxTeamsPerUser': league.max_teams_per_user,
                    'createdAt': league.created_at.isoformat(),
                    'creator': {
                        'userId': str(creator.id),
                        'displayName': creator.display_name
                    } if creator else None
                },
                'members': members,
                'stats': {
                    'totalMembers': len(members),
                    'totalPicks': total_picks,
                    'maxPossiblePicks': len(members) * league.max_teams_per_user
                }
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get league settings error: {str(e)}")
        import traceback
        print(f"Get league settings traceback: {traceback.format_exc()}")
        return error_response('Failed to get league settings', 500)
