import json
from typing import Any, Dict, Optional

def cors_headers() -> Dict[str, str]:
    """Standard CORS headers for all responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    }

def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create a successful API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **cors_headers()
        },
        'body': json.dumps({
            'success': True,
            'data': data
        })
    }

def error_response(message: str, status_code: int = 400, error_type: str = 'ClientError') -> Dict[str, Any]:
    """Create an error API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **cors_headers()
        },
        'body': json.dumps({
            'success': False,
            'error': {
                'type': error_type,
                'message': message
            }
        })
    }

def validation_error_response(errors: Dict[str, str]) -> Dict[str, Any]:
    """Create a validation error response"""
    return {
        'statusCode': 422,
        'headers': {
            'Content-Type': 'application/json',
            **cors_headers()
        },
        'body': json.dumps({
            'success': False,
            'error': {
                'type': 'ValidationError',
                'message': 'Validation failed',
                'details': errors
            }
        })
    }

def not_found_response(resource: str = 'Resource') -> Dict[str, Any]:
    """Create a not found response"""
    return error_response(f'{resource} not found', 404, 'NotFoundError')

def unauthorized_response(message: str = 'Unauthorized') -> Dict[str, Any]:
    """Create an unauthorized response"""
    return error_response(message, 401, 'UnauthorizedError')

def server_error_response(message: str = 'Internal server error') -> Dict[str, Any]:
    """Create a server error response"""
    return error_response(message, 500, 'ServerError')
