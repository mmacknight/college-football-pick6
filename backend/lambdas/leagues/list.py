import json
import sys
import os

# Import from layer
from shared.database import get_db_session, League, LeagueTeam, User
from shared.responses import success_response, error_response
from shared.auth import require_auth, get_user_id_from_event
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

@require_auth
def lambda_handler(event, context):
    """Get user's leagues"""
    try:
        user_id = get_user_id_from_event(event)
        
        db = get_db_session()
        try:
            # Get leagues where user is either creator OR member
            # First get leagues created by user
            created_leagues = db.query(League)\
                .filter(League.created_by == user_id)\
                .all()
            
            # Then get leagues where user is a member (has picked teams)
            member_leagues = db.query(League)\
                .join(LeagueTeam, League.id == LeagueTeam.league_id)\
                .filter(LeagueTeam.user_id == user_id)\
                .all()
            
            # Combine and deduplicate
            all_leagues = {league.id: league for league in created_leagues + member_leagues}
            
            leagues_data = []
            for league in all_leagues.values():
                # Count members
                member_count = db.query(LeagueTeam.user_id)\
                    .filter(LeagueTeam.league_id == league.id)\
                    .distinct()\
                    .count()
                
                # Check if user has teams in this league
                user_team_count = db.query(LeagueTeam)\
                    .filter(and_(
                        LeagueTeam.league_id == league.id,
                        LeagueTeam.user_id == user_id
                    ))\
                    .count()
                
                leagues_data.append({
                    'id': str(league.id),
                    'name': league.name,
                    'season': league.season,
                    'status': league.status,
                    'joinCode': league.join_code,
                    'memberCount': member_count,
                    'userTeamCount': user_team_count,
                    'maxTeamsPerUser': league.max_teams_per_user,
                    'createdAt': league.created_at.isoformat(),
                    'isCreator': str(league.created_by) == str(user_id)
                })
            
            # Sort by most recent first
            leagues_data.sort(key=lambda x: x['createdAt'], reverse=True)
            
            return success_response(leagues_data)
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"List leagues error: {str(e)}")
        return error_response('Failed to get leagues', 500)
