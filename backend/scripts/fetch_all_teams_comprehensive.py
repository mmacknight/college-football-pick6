#!/usr/bin/env python3
"""
Comprehensive script to fetch ALL college football teams from multiple sources
"""

import json
import os
import sys
import requests
from typing import List, Dict

CFB_API_BASE = "https://api.collegefootballdata.com"

def get_cfb_api_key():
    """Get CFB API key from environment or parameter store"""
    api_key = os.getenv('CFB_API_KEY')
    if not api_key:
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
            return None
    return api_key

def fetch_teams_all_endpoint(year: str = "2025") -> List[Dict]:
    """Try the general /teams endpoint which might include both FBS and FCS"""
    api_key = get_cfb_api_key()
    if not api_key:
        raise Exception("CFB_API_KEY not available")
    
    headers = {'Authorization': f'Bearer {api_key}'}
    
    try:
        print(f"Trying /teams endpoint for {year}...")
        response = requests.get(
            f"{CFB_API_BASE}/teams",
            headers=headers,
            params={'year': year}
        )
        response.raise_for_status()
        teams = response.json()
        
        # Analyze the results
        fbs_count = len([t for t in teams if t.get('classification') == 'fbs'])
        fcs_count = len([t for t in teams if t.get('classification') == 'fcs'])
        
        print(f"✅ Found {len(teams)} total teams (FBS: {fbs_count}, FCS: {fcs_count})")
        return teams
        
    except Exception as e:
        print(f"❌ /teams endpoint failed: {e}")
        return []

def fetch_teams_by_year_range() -> List[Dict]:
    """Try multiple years to find FCS data"""
    api_key = get_cfb_api_key()
    if not api_key:
        raise Exception("CFB_API_KEY not available")
    
    headers = {'Authorization': f'Bearer {api_key}'}
    all_teams = []
    missing_ids = [282, 304, 2710]
    found_missing = {}
    
    # Try years from 2024 down to 2020 to find FCS data
    for year in ['2024', '2023', '2022', '2021', '2020']:
        try:
            print(f"\nTrying FCS teams for {year}...")
            response = requests.get(
                f"{CFB_API_BASE}/teams/fcs",
                headers=headers,
                params={'year': year}
            )
            response.raise_for_status()
            fcs_teams = response.json()
            
            if fcs_teams:
                print(f"✅ Found {len(fcs_teams)} FCS teams for {year}")
                
                # Check for our missing IDs
                for team in fcs_teams:
                    if team.get('id') in missing_ids and team.get('id') not in found_missing:
                        found_missing[team['id']] = {
                            'year': year,
                            'school': team['school'],
                            'classification': team.get('classification'),
                            'data': team
                        }
                        print(f"🎯 Found missing ID {team['id']}: {team['school']}")
                
                # If this is the most recent year with data, save these teams
                if year == '2024' or not all_teams:
                    all_teams = fcs_teams
                    
                # If we found all missing schools, we can stop
                if len(found_missing) >= len(missing_ids):
                    break
                    
            else:
                print(f"⚠️  No FCS teams for {year}")
                
        except Exception as e:
            print(f"⚠️  Could not fetch FCS teams for {year}: {e}")
    
    return all_teams, found_missing

def main():
    """Main function"""
    print("🏈 Comprehensive College Football Teams Fetch")
    print("=" * 60)
    
    # First, try to get 2025 data from /teams endpoint
    teams_2025 = fetch_teams_all_endpoint("2025")
    
    if teams_2025:
        missing_ids = [282, 304, 2710]
        found_missing = []
        for team in teams_2025:
            if team.get('id') in missing_ids:
                found_missing.append((team['id'], team['school'], team.get('classification', 'unknown')))
        
        if found_missing:
            print(f"🎯 Found all missing school IDs in 2025 data:")
            for school_id, name, classification in found_missing:
                print(f"   ID {school_id}: {name} ({classification})")
            
            # Save 2025 data
            output_file = "/Users/mitchmacknight/ios_pick6/backend/data/cfb_teams_2025_complete.json"
            with open(output_file, 'w') as f:
                json.dump(teams_2025, f, indent=2)
            print(f"💾 Saved complete 2025 data to {output_file}")
            return
    
    # If 2025 doesn't have what we need, try the year range approach
    print("\n" + "="*60)
    print("Searching historical data for FCS teams...")
    
    fcs_teams, found_missing = fetch_teams_by_year_range()
    
    if found_missing:
        print(f"\n🎯 Found missing school IDs:")
        for school_id, info in found_missing.items():
            print(f"   ID {school_id}: {info['school']} ({info['classification']}) from {info['year']}")
        
        # Load the existing 2025 FBS data
        fbs_2025_file = "/Users/mitchmacknight/ios_pick6/backend/data/cfb_teams_2025.json"
        if os.path.exists(fbs_2025_file):
            with open(fbs_2025_file, 'r') as f:
                fbs_2025 = json.load(f)
            print(f"\n📂 Loaded {len(fbs_2025)} FBS teams from existing 2025 file")
            
            # Combine FBS 2025 + any missing FCS teams we found
            all_teams = fbs_2025.copy()
            for school_id, info in found_missing.items():
                all_teams.append(info['data'])
            
            # Save combined data
            output_file = "/Users/mitchmacknight/ios_pick6/backend/data/cfb_teams_2025_combined.json"
            with open(output_file, 'w') as f:
                json.dump(all_teams, f, indent=2)
            
            print(f"💾 Saved combined data ({len(all_teams)} teams) to {output_file}")
            print(f"   - FBS 2025: {len(fbs_2025)} teams")
            print(f"   - Missing FCS: {len(found_missing)} teams")
            
        else:
            print(f"❌ Could not find existing FBS 2025 file: {fbs_2025_file}")
    
    else:
        print("❌ Could not find the missing school IDs in any year")

if __name__ == "__main__":
    main()

