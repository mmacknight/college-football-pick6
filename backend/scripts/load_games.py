#!/usr/bin/env python3
"""
Direct script to load CFB games from CollegeFootballData API
Run this to initialize your games for 2024 and 2025 seasons
"""

import os
import sys
import json

# Add the parent directory to sys.path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Now import from lambdas
from lambdas.admin.games_load import lambda_handler

def main():
    print("🏈 Loading College Football Games...")
    print("=" * 50)
    
    # Create a mock Lambda event
    event = {
        'body': json.dumps({
            'seasons': ['2024', '2025']
        })
    }
    
    context = None  # We don't need context for this script
    
    try:
        # Call the Lambda function directly
        result = lambda_handler(event, context)
        
        # Parse the response
        if result['statusCode'] == 200:
            data = json.loads(result['body'])['data']
            print(f"✅ Success!")
            print(f"   Seasons loaded: {data['seasons']}")
            print(f"   Total games added: {data['total_games_added']}")
            print(f"   Total games skipped: {data['total_games_skipped']}")
            print(f"   Message: {data['message']}")
        else:
            error_data = json.loads(result['body'])
            print(f"❌ Error: {error_data['error']['message']}")
            
    except Exception as e:
        print(f"❌ Failed to load games: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
