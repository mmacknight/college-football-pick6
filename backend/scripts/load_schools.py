#!/usr/bin/env python3
"""
Direct script to load CFB schools from CollegeFootballData API
Run this to initialize your season with real data
"""

import os
import sys
import json

# Add the parent directory to sys.path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Now import from lambdas
from lambdas.admin.season_init import lambda_handler

def main():
    print("🏈 Loading College Football Schools...")
    print("=" * 50)
    
    # Create a mock Lambda event
    event = {
        'body': json.dumps({
            'season': '2024'
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
            print(f"   Schools added: {data['schools_added']}")
            print(f"   Schools skipped: {data['schools_skipped']}")
            print(f"   Total teams: {data['total_teams']}")
            print(f"   Message: {data['message']}")
        else:
            error_data = json.loads(result['body'])
            print(f"❌ Error: {error_data['error']['message']}")
            
    except Exception as e:
        print(f"❌ Failed to load schools: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
