#!/usr/bin/env python3
"""
Test Draft APIs Script
Tests all draft-related endpoints to ensure they work correctly
"""

import requests
import json
import sys
import os

# Configuration
BASE_URL = "http://127.0.0.1:3001"
TEST_EMAIL = "mike@test.com"
TEST_PASSWORD = "test123"

def login_and_get_token():
    """Login and get JWT token"""
    print("🔐 Logging in...")
    
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        token = data['data']['token']
        user_id = data['data']['user']['id']
        print(f"✅ Login successful - User ID: {user_id}")
        return token, user_id
    else:
        print(f"❌ Login failed: {response.text}")
        return None, None

def test_league_creation(token):
    """Create a test league"""
    print("\n🏈 Creating test league...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/leagues", 
        headers=headers,
        json={
            "name": "Draft Test League",
            "season": 2024
        }
    )
    
    if response.status_code == 201:
        data = response.json()
        league_id = data['data']['id']
        join_code = data['data']['joinCode']
        print(f"✅ League created - ID: {league_id}, Join Code: {join_code}")
        return league_id, join_code
    else:
        print(f"❌ League creation failed: {response.text}")
        return None, None

def test_league_join(token, join_code):
    """Join the test league with additional users"""
    print(f"\n👥 Joining league with code {join_code}...")
    
    # Test users to join
    test_users = [
        {"email": "sarah@test.com", "name": "Sarah's Squad"},
        {"email": "alex@test.com", "name": "Alex's Aces"},
        {"email": "jordan@test.com", "name": "Jordan's Juggernauts"}
    ]
    
    joined_count = 0
    for user in test_users:
        # Login as test user
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": user["email"],
            "password": "test123"
        })
        
        if login_response.status_code == 200:
            user_token = login_response.json()['data']['token']
            
            # Join league
            headers = {"Authorization": f"Bearer {user_token}"}
            join_response = requests.post(f"{BASE_URL}/leagues/join",
                headers=headers,
                json={
                    "joinCode": join_code,
                    "teamName": user["name"]
                }
            )
            
            if join_response.status_code == 200:
                joined_count += 1
                print(f"  ✅ {user['email']} joined successfully")
            else:
                print(f"  ❌ {user['email']} failed to join: {join_response.text}")
    
    print(f"✅ {joined_count} additional users joined the league")
    return joined_count

def test_draft_status(token, league_id):
    """Test draft status endpoint"""
    print(f"\n📊 Testing draft status for league {league_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/leagues/{league_id}/draft-status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"✅ Draft Status Retrieved:")
        print(f"  - League Status: {data.get('leagueStatus')}")
        print(f"  - Draft Status: {data.get('draftStatus')}")
        print(f"  - Total Users: {data.get('totalUsers')}")
        print(f"  - Total Picks: {data.get('totalPicks')}")
        print(f"  - Current Pick: {data.get('currentPickOverall')}")
        return data
    else:
        print(f"❌ Draft status failed: {response.text}")
        return None

def test_start_draft(token, league_id):
    """Test starting the draft"""
    print(f"\n🚀 Starting draft for league {league_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/leagues/{league_id}/start-draft", headers=headers)
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"✅ Draft Started Successfully:")
        print(f"  - Draft Order: {len(data.get('draftOrder', []))} players")
        for i, player in enumerate(data.get('draftOrder', [])):
            print(f"    {i+1}. {player['displayName']} ({player['teamName']})")
        return data
    else:
        print(f"❌ Start draft failed: {response.text}")
        return None

def test_my_teams(token, league_id):
    """Test my teams endpoint"""
    print(f"\n👤 Testing my teams for league {league_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/leagues/{league_id}/my-teams", headers=headers)
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"✅ My Teams Retrieved:")
        print(f"  - Teams Drafted: {len(data.get('teams', []))}")
        print(f"  - Remaining Picks: {data.get('remainingPicks', 0)}")
        return data
    else:
        print(f"❌ My teams failed: {response.text}")
        return None

def test_draft_board(token, league_id):
    """Test draft board endpoint"""
    print(f"\n📋 Testing draft board for league {league_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/leagues/{league_id}/draft-board", headers=headers)
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"✅ Draft Board Retrieved:")
        print(f"  - Total Picks: {data.get('totalPicks', 0)}")
        print(f"  - Picks Made: {len(data.get('picks', []))}")
        return data
    else:
        print(f"❌ Draft board failed: {response.text}")
        return None

def test_team_selection(token, league_id):
    """Test making a draft pick"""
    print(f"\n🎯 Testing team selection...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First get available schools
    schools_response = requests.get(f"{BASE_URL}/schools", headers=headers)
    if schools_response.status_code != 200:
        print(f"❌ Could not get schools: {schools_response.text}")
        return None
    
    schools = schools_response.json()['data']['schools']
    # Pick Alabama (typically ID 333)
    alabama = next((s for s in schools if s['name'] == 'Alabama'), schools[0])
    
    # Make the pick
    response = requests.post(f"{BASE_URL}/teams/select",
        headers=headers,
        json={
            "leagueId": league_id,
            "schoolId": alabama['id']
        }
    )
    
    if response.status_code == 201:
        data = response.json()['data']
        print(f"✅ Team Selected Successfully:")
        print(f"  - School: {data['school']['name']}")
        print(f"  - Draft Round: {data['draftRound']}")
        print(f"  - Pick Overall: {data['draftPickOverall']}")
        return data
    else:
        print(f"❌ Team selection failed: {response.text}")
        return None

def main():
    """Run all draft API tests"""
    print("🧪 Testing Draft APIs")
    print("=" * 50)
    
    # Login and get token
    token, user_id = login_and_get_token()
    if not token:
        return
    
    # Create test league
    league_id, join_code = test_league_creation(token)
    if not league_id:
        return
    
    # Join additional users
    test_league_join(token, join_code)
    
    # Test draft status (pre-draft)
    test_draft_status(token, league_id)
    
    # Start the draft
    test_start_draft(token, league_id)
    
    # Test draft status (post-start)
    test_draft_status(token, league_id)
    
    # Test my teams
    test_my_teams(token, league_id)
    
    # Test draft board
    test_draft_board(token, league_id)
    
    # Test team selection
    test_team_selection(token, league_id)
    
    # Test draft status after pick
    test_draft_status(token, league_id)
    
    # Test updated my teams
    test_my_teams(token, league_id)
    
    # Test updated draft board
    test_draft_board(token, league_id)
    
    print("\n🎉 All draft API tests completed!")

if __name__ == "__main__":
    main()
