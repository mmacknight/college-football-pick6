#!/usr/bin/env python3
"""
Fetch ALL college football teams (FBS + FCS) for 2025 season from CollegeFootballData API
and save to JSON file for loading into database.
"""

import json
import os
import sys
import requests
from typing import List, Dict

# CollegeFootballData API configuration
CFB_API_BASE = "https://api.collegefootballdata.com"

def get_cfb_api_key():
    """Get CFB API key from environment or parameter store"""
    api_key = os.getenv('CFB_API_KEY')
    if not api_key:
        # Try to get from AWS Parameter Store
        try:
            import boto3
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(
                Name='/pick6/prod/cfb-api-key', 
                WithDecryption=True
            )
            api_key = response['Parameter']['Value']
        except Exception as e:
            print(f"Could not get API key from Parameter Store: {e}")
            print("Please set CFB_API_KEY environment variable or ensure AWS credentials are configured")
            return None
    return api_key

def fetch_all_teams(year: str = "2025") -> List[Dict]:
    """Fetch ALL teams (FBS + FCS) from CollegeFootballData API"""
    api_key = get_cfb_api_key()
    if not api_key:
        raise Exception("CFB_API_KEY not available")
    
    headers = {'Authorization': f'Bearer {api_key}'}
    all_teams = []
    
    try:
        # Fetch FBS teams
        print(f"Fetching FBS teams for {year}...")
        response = requests.get(
            f"{CFB_API_BASE}/teams/fbs",
            headers=headers,
            params={'year': year}
        )
        response.raise_for_status()
        fbs_teams = response.json()
        all_teams.extend(fbs_teams)
        print(f"✅ Found {len(fbs_teams)} FBS teams")
        
        # Fetch FCS teams
        print(f"Fetching FCS teams for {year}...")
        try:
            response = requests.get(
                f"{CFB_API_BASE}/teams/fcs",
                headers=headers,
                params={'year': year}
            )
            response.raise_for_status()
            fcs_teams = response.json()
            if fcs_teams:
                all_teams.extend(fcs_teams)
                print(f"✅ Found {len(fcs_teams)} FCS teams")
            else:
                print(f"⚠️  No FCS teams found for {year}")
                fcs_teams = []
        except Exception as e:
            print(f"⚠️  Could not fetch FCS teams for {year}: {e}")
            print("Continuing with FBS teams only...")
            fcs_teams = []
        
        print(f"🏈 Total teams: {len(all_teams)} (FBS: {len(fbs_teams)}, FCS: {len(fcs_teams)})")
        
        # Check for our missing school IDs
        missing_ids = [282, 304, 2710]
        found_missing = []
        for team in all_teams:
            if team.get('id') in missing_ids:
                found_missing.append((team['id'], team['school'], team.get('classification', 'unknown')))
        
        if found_missing:
            print(f"🎯 Found missing school IDs:")
            for school_id, name, classification in found_missing:
                print(f"   ID {school_id}: {name} ({classification})")
        else:
            print(f"⚠️  Missing school IDs not found: {missing_ids}")
        
        return all_teams
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching teams from API: {str(e)}")
        raise

def save_teams_to_file(teams: List[Dict], year: str = "2025"):
    """Save teams data to JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    output_file = os.path.join(data_dir, f'cfb_teams_{year}.json')
    
    with open(output_file, 'w') as f:
        json.dump(teams, f, indent=2)
    
    print(f"💾 Saved {len(teams)} teams to {output_file}")
    return output_file

def main():
    """Main function"""
    year = "2025"
    
    print(f"🏈 Fetching ALL College Football Teams for {year}...")
    print("=" * 60)
    
    try:
        # Fetch all teams
        teams = fetch_all_teams(year)
        
        if not teams:
            print("❌ No teams found!")
            sys.exit(1)
        
        # Save to file
        output_file = save_teams_to_file(teams, year)
        
        print("\n✅ Success! Next steps:")
        print(f"   1. Review the data in: {output_file}")
        print(f"   2. Load schools: python3 scripts/load_schools_from_file.py")
        print(f"      (Update the script to use cfb_teams_{year}.json)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
