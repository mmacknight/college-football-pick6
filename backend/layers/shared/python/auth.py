import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
import json

JWT_SECRET = os.getenv('JWT_SECRET', 'your-development-secret-key')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 30

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

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
            from responses import unauthorized_response
            return unauthorized_response('Invalid or missing authentication token')
        
        # Add user info to event for use in the function
        event['user'] = user
        return func(event, context)
    
    return wrapper

def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Get user ID from authenticated event"""
    user = event.get('user')
    return user.get('user_id') if user else None
