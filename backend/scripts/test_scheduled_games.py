#!/usr/bin/env python3
"""
Test script for the scheduled games loader
Validates that the new Lambda function works correctly before deployment
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to sys.path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from local-env.json (same as dev_server.py does)
def load_local_env():
    """Load environment variables from local-env.json"""
    env_file = os.path.join(os.path.dirname(__file__), '..', 'local-env.json')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_data = json.load(f)
            for key, value in env_data.get('Parameters', {}).items():
                os.environ[key] = value
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️ Environment file not found: {env_file}")

# Load environment first
load_local_env()

# Now import from lambdas
from lambdas.admin.games_load_scheduled import lambda_handler as scheduled_handler
from lambdas.admin.games_load import lambda_handler as bulk_handler

def test_scheduled_loader():
    """Test the scheduled game loader function"""
    print("🏈 Testing Scheduled Game Loader...")
    print("=" * 50)
    
    # Test 1: Basic scheduled update (current week only)
    print("\n📋 Test 1: Basic Scheduled Update")
    event = {
        'body': json.dumps({
            'season': 2025
        })
    }
    
    try:
        result = scheduled_handler(event, None)
        
        if result['statusCode'] == 200:
            data = json.loads(result['body'])['data']
            print(f"✅ Scheduled update successful!")
            print(f"   Season: {data['season']}")
            print(f"   Week: {data['week']}")
            print(f"   Games updated: {data['games_updated']}")
            print(f"   Games added: {data['games_added']}")
            print(f"   Is Saturday CST: {data['is_saturday_cst']}")
        else:
            error_data = json.loads(result['body'])
            print(f"❌ Error: {error_data['error']['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during scheduled test: {str(e)}")
        return False
    
    # Test 2: EventBridge-style invocation (no body)
    print("\n📋 Test 2: EventBridge-Style Invocation")
    event = {}  # Empty event like EventBridge sends
    
    try:
        result = scheduled_handler(event, None)
        
        if result['statusCode'] == 200:
            data = json.loads(result['body'])['data']
            print(f"✅ EventBridge-style invocation successful!")
            print(f"   Auto-detected season: {data['season']}")
            print(f"   Current week: {data['week']}")
        else:
            error_data = json.loads(result['body'])
            print(f"❌ Error: {error_data['error']['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during EventBridge test: {str(e)}")
        return False
    
    # Test 3: Error handling for force_all_weeks
    print("\n📋 Test 3: Error Handling for Bulk Load Request")
    event = {
        'body': json.dumps({
            'season': 2025,
            'force_all_weeks': True
        })
    }
    
    try:
        result = scheduled_handler(event, None)
        
        if result['statusCode'] == 400:
            print(f"✅ Correctly rejected bulk load request!")
        else:
            print(f"❌ Should have rejected force_all_weeks request")
            return False
            
    except Exception as e:
        print(f"❌ Exception during error handling test: {str(e)}")
        return False
    
    return True

def test_bulk_loader():
    """Test that the existing bulk loader still works"""
    print("\n🏈 Testing Bulk Game Loader...")
    print("=" * 50)
    
    # Note: This will actually load games, so use a small test
    event = {
        'body': json.dumps({
            'seasons': ['2025']  # Just test one season
        })
    }
    
    try:
        print("⚠️ This will load games from the API - continuing in 3 seconds...")
        import time
        time.sleep(3)
        
        result = bulk_handler(event, None)
        
        if result['statusCode'] == 200:
            data = json.loads(result['body'])['data']
            print(f"✅ Bulk loader test successful!")
            print(f"   Seasons: {data['seasons']}")
            print(f"   Total games added: {data['total_games_added']}")
            print(f"   Total games skipped: {data['total_games_skipped']}")
            return True
        else:
            error_data = json.loads(result['body'])
            print(f"❌ Error: {error_data['error']['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during bulk loader test: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🧪 Game Loading System Test Suite")
    print("=" * 60)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    success = True
    
    # Test scheduled loader
    if not test_scheduled_loader():
        success = False
    
    # Test bulk loader (commented out to avoid loading too much data)
    # Uncomment if you want to test the bulk loader too
    # if not test_bulk_loader():
    #     success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! System ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please review and fix before deployment.")
        return 1

if __name__ == "__main__":
    exit(main())
