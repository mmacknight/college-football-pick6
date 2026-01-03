import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
import json

try:
    from .parameter_store import get_jwt_secret
    JWT_SECRET = get_jwt_secret()
except:
    # Fallback for local development
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-development-secret-key')

JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 30

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 with SHA256"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{hashed.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, hash_value = hashed.split(':')
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hash_value == test_hash.hex()
    except ValueError:
        return False

def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def extract_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract user info from Lambda event headers"""
    headers = event.get('headers', {})
    
    # Handle different header formats (case insensitive)
    auth_header = None
    for key, value in headers.items():
        if key.lower() == 'authorization':
            auth_header = value
            break
    
    if not auth_header:
        return None
    
    # Extract token from "Bearer <token>"
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    return decode_jwt_token(token)

def require_auth(func):
    """Decorator to require authentication for Lambda functions"""
    @wraps(func)
    def wrapper(event, context):
        user = extract_user_from_event(event)
        if not user:
            from shared.responses import unauthorized_response
            return unauthorized_response('Invalid or missing authentication token')
        
        # Add user info to event for use in the function
        event['user'] = user
        return func(event, context)
    
    return wrapper

def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Get user ID from authenticated event"""
    user = event.get('user')
    return user.get('user_id') if user else None

def get_user_uuid_from_event(event: Dict[str, Any]) -> Optional['UUID']:
    """Get user UUID from authenticated event (converted from string)"""
    from uuid import UUID
    user_id_str = get_user_id_from_event(event)
    if not user_id_str:
        return None
    try:
        return UUID(user_id_str)
    except (ValueError, TypeError):
        return None

def is_league_creator(league, event: Dict[str, Any]) -> bool:
    """Check if the authenticated user is the creator of the league"""
    user_uuid = get_user_uuid_from_event(event)
    if not user_uuid:
        return False
    return league.created_by == user_uuid

def require_league_creator(league, event: Dict[str, Any], action_name: str = "perform this action"):
    """Check if user is league creator, return error response if not"""
    if not is_league_creator(league, event):
        from shared.responses import error_response
        return error_response(f'Only the league creator can {action_name}', 403)
    return None
