import json
import sys
import os

# Import from layer  
from shared.database import get_db_session, School, LeagueTeam, LeagueTeamSchoolAssignment
from shared.responses import success_response, error_response
from shared.auth import require_auth
from sqlalchemy import and_, not_

def lambda_handler(event, context):
    """Get available schools for team selection in a league"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        league_id = query_params.get('league_id')
        conference = query_params.get('conference')
        available_only = query_params.get('available_only', 'false').lower() == 'true'
        
        db = get_db_session()
        try:
            # Define FBS conferences to filter to only FBS schools
            fbs_conferences = [
                'ACC', 'American Athletic', 'Big 12', 'Big Ten', 'Conference USA',
                'FBS Independents', 'Mid-American', 'Mountain West', 'Pac-12', 
                'SEC', 'Sun Belt'
            ]
            
            # Start with only FBS schools by filtering by conference
            query = db.query(School).filter(School.conference.in_(fbs_conferences)).order_by(School.name)
            
            # Filter by conference if specified
            if conference:
                query = query.filter(School.conference == conference)
            
            # If league_id provided and available_only is true, exclude already picked teams
            if league_id and available_only:
                taken_school_ids = db.query(LeagueTeamSchoolAssignment.school_id)\
                    .filter(LeagueTeamSchoolAssignment.league_id == league_id)\
                    .subquery()
                query = query.filter(not_(School.id.in_(taken_school_ids)))
            
            schools = query.all()
            
            # Format response
            schools_data = []
            for school in schools:
                # Check if already taken in this league
                is_taken = False
                if league_id:
                    taken = db.query(LeagueTeamSchoolAssignment)\
                        .filter(and_(LeagueTeamSchoolAssignment.league_id == league_id, 
                                   LeagueTeamSchoolAssignment.school_id == school.id))\
                        .first()
                    is_taken = taken is not None
                
                schools_data.append({
                    'id': school.id,
                    'name': school.name,
                    'mascot': school.mascot,
                    'abbreviation': school.abbreviation,
                    'conference': school.conference,
                    'primaryColor': school.primary_color,
                    'secondaryColor': school.secondary_color,
                    'isTaken': is_taken
                })
            
            # Get unique FBS conferences for filtering
            conferences = db.query(School.conference)\
                .filter(School.conference.in_(fbs_conferences))\
                .filter(School.conference.isnot(None))\
                .distinct()\
                .order_by(School.conference)\
                .all()
            conference_list = [c[0] for c in conferences]
            
            return success_response({
                'schools': schools_data,
                'conferences': conference_list,
                'total': len(schools_data)
            })
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Get schools error: {str(e)}")
        print(f"Get schools error type: {type(e)}")
        import traceback
        print(f"Get schools traceback: {traceback.format_exc()}")
        return error_response('Failed to get schools', 500)
