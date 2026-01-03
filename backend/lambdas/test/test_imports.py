import json
import sys
import traceback

def lambda_handler(event, context):
    """Test Lambda layer imports"""
    
    results = {
        "success": True,
        "imports": {},
        "python_path": sys.path,
        "errors": []
    }
    
    # Test standard imports
    test_modules = [
        ("json", "json"),
        ("boto3", "boto3"),
        ("sqlalchemy", "sqlalchemy"),
        ("jwt", "jwt"),
        ("pg8000", "pg8000")
    ]
    
    for module_name, import_name in test_modules:
        try:
            exec(f"import {import_name}")
            results["imports"][module_name] = "✅ SUCCESS"
        except Exception as e:
            results["imports"][module_name] = f"❌ FAILED: {str(e)}"
            results["errors"].append(f"{module_name}: {str(e)}")
            results["success"] = False
    
    # Test shared layer imports
    shared_modules = [
        ("shared.database", "shared.database"),
        ("shared.auth", "shared.auth"),
        ("shared.responses", "shared.responses"),
        ("shared.parameter_store", "shared.parameter_store")
    ]
    
    for module_name, import_name in shared_modules:
        try:
            exec(f"from {import_name} import *")
            results["imports"][module_name] = "✅ SUCCESS"
        except Exception as e:
            results["imports"][module_name] = f"❌ FAILED: {str(e)}"
            results["errors"].append(f"{module_name}: {str(e)}")
            results["success"] = False
    
    # Return response
    if results["success"]:
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'message': 'All imports successful!',
                'data': results
            })
        }
    else:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
            },
            'body': json.dumps({
                'success': False,
                'message': 'Import errors detected',
                'data': results
            })
        }
