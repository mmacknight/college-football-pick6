import json
import sys
import os
import requests
from typing import List, Dict

# Import from layer
sys.path.append('/opt/python/python')

from database import get_db_session, School
from sqlalchemy import text
from responses import success_response, error_response

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"
CFB_API_KEY = os.getenv('CFB_API_KEY')

# Team color mappings for major teams (CollegeFootballData doesn't always have colors)
TEAM_COLORS = {
    'Alabama': '#9E1B32',
    'Georgia': '#BA0C2F', 
    'Michigan': '#00274C',
    'Texas': '#BF5700',
    'Ohio State': '#BB0000',
    'Oregon': '#18453B',
    'Clemson': '#F66733',
    'USC': '#990000',
    'Miami': '#F47321',
    'Florida': '#0021A5',
    'LSU': '#461D7C',
    'Notre Dame': '#0C2340',
    'Oklahoma': '#841617',
    'Wisconsin': '#C5050C',
    'Penn State': '#041E42',
    'Tennessee': '#FF8200',
    'Auburn': '#0C2340',
    'Texas A&M': '#500000',
    'Florida State': '#782F40',
    'UCLA': '#2774AE',
    'Stanford': '#8C1515',
    'Washington': '#4B2E83',
    'Utah': '#CC0000',
    'Kansas': '#0051BA',
    'North Carolina': '#4B9CD3',
    'Virginia Tech': '#861F41',
    'Iowa': '#FFCD00',
    'Nebraska': '#D00000'
}

def get_team_color(school_name: str, api_color: str = None) -> str:
    """Get team primary color, with fallback logic"""
    # First try exact match
    if school_name in TEAM_COLORS:
        return TEAM_COLORS[school_name]
    
    # Try partial matches for common variations
    for team, color in TEAM_COLORS.items():
        if team.lower() in school_name.lower() or school_name.lower() in team.lower():
            return color
    
    # Use API provided color if available
    if api_color and api_color.startswith('#'):
        return api_color
    
    # Default fallback color
    return '#000000'

def fetch_teams_from_api(year: str = "2024") -> List[Dict]:
    """Fetch all FBS teams from CollegeFootballData API"""
    if not CFB_API_KEY:
        raise Exception("CFB_API_KEY environment variable not set")
    
    headers = {'Authorization': f'Bearer {CFB_API_KEY}'}
    
    try:
        # Get FBS teams for the season
        response = requests.get(
            f"{CFB_API_BASE}/teams/fbs",
            headers=headers,
            params={'year': year}
        )
        response.raise_for_status()
        teams = response.json()
        
        print(f"Fetched {len(teams)} teams from CollegeFootballData API")
        return teams
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teams from API: {str(e)}")
        raise

def normalize_school_id(school_name: str) -> str:
    """Convert school name to consistent ID format"""
    # Remove common suffixes and normalize
    name = school_name.lower()
    name = name.replace(' university', '')
    name = name.replace(' state university', ' state')
    name = name.replace(' college', '')
    name = name.replace('university of ', '')
    name = name.replace(' ', '')
    name = name.replace('-', '')
    name = name.replace('.', '')
    
    # Handle special cases
    special_cases = {
        'ohiostate': 'ohiostate',
        'notredame': 'notredame',
        'texasam': 'texasam',
        'floridastate': 'floridastate',
        'virginiatech': 'virginiatech',
        'northcarolina': 'northcarolina',
        'southernmethodist': 'smu',
        'texaschristian': 'tcu',
        'brighamyoung': 'byu'
    }
    
    return special_cases.get(name, name)

def lambda_handler(event, context):
    """Initialize season by loading all FBS schools"""
    try:
        # Get season year from event or default to current
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        season = body.get('season', '2024')
        
        print(f"Initializing season {season}...")
        
        # Fetch teams from API
        api_teams = fetch_teams_from_api(season)
        
        if not api_teams:
            return error_response("No teams found from API", 400)
        
        # Database operations
        db = get_db_session()
        try:
            # Clear existing data for clean slate (order matters due to foreign keys)
            print("Clearing existing data...")
            db.execute(text("DELETE FROM games"))
            db.execute(text("DELETE FROM league_teams")) 
            db.execute(text("DELETE FROM schools"))
            
            schools_added = 0
            schools_skipped = 0
            
            for team in api_teams:
                try:
                    school_id = normalize_school_id(team['school'])
                    
                    # Get team colors
                    primary_color = get_team_color(
                        team['school'], 
                        team.get('color')  # API primary color
                    )
                    
                    secondary_color = team.get('alternateColor')
                    if secondary_color and not secondary_color.startswith('#'):
                        secondary_color = f"#{secondary_color}" if secondary_color else None
                    
                    # Create school record
                    school = School(
                        id=team.get('id'),  # CollegeFootballData team_id
                        team_slug=school_id,
                        abbreviation=team.get('abbreviation', ''),
                        name=team['school'],
                        mascot=team.get('mascot', ''),
                        conference=team.get('conference', ''),
                        primary_color=primary_color,
                        secondary_color=secondary_color
                    )
                    
                    db.add(school)
                    schools_added += 1
                    
                    print(f"Added: {team['school']} ({school_id}) - {team.get('conference', 'No Conference')}")
                    
                except Exception as e:
                    print(f"Error adding school {team.get('school', 'Unknown')}: {str(e)}")
                    schools_skipped += 1
                    continue
            
            # Commit all changes
            db.commit()
            
            print(f"Season {season} initialization complete!")
            print(f"Schools added: {schools_added}")
            print(f"Schools skipped: {schools_skipped}")
            
            return success_response({
                'season': season,
                'schools_added': schools_added,
                'schools_skipped': schools_skipped,
                'total_teams': len(api_teams),
                'message': f'Successfully initialized season {season} with {schools_added} schools'
            })
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        print(f"Season initialization error: {str(e)}")
        return error_response(f'Season initialization failed: {str(e)}', 500)
