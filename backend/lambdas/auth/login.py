import json
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, User
from responses import success_response, error_response, validation_error_response
from auth import verify_password, create_jwt_token

def lambda_handler(event, context):
    """Handle user login"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        
        # Validate input
        errors = {}
        if not email:
            errors['email'] = 'Email is required'
        if not password:
            errors['password'] = 'Password is required'
        
        if errors:
            return validation_error_response(errors)
        
        # Database operations
        db = get_db_session()
        try:
            # Find user by email
            user = db.query(User).filter(User.email == email).first()
            
            if not user or not verify_password(password, user.password_hash):
                return error_response('Invalid email or password', 401)
            
            # Create JWT token
            token = create_jwt_token(str(user.id), user.email)
            
            # Return user data and token
            return success_response({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'displayName': user.display_name,
                    'createdAt': user.created_at.isoformat()
                },
                'token': token
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response('Login failed', 500)