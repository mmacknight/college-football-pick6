import json
import sys
import os
import re

# Import from layer
from shared.database import get_db_session, User
from shared.responses import success_response, error_response, validation_error_response
from shared.auth import hash_password, create_jwt_token
from sqlalchemy.exc import IntegrityError

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def lambda_handler(event, context):
    """Handle user signup"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        email = body.get('email', '').strip().lower()
        password = body.get('password', '')
        display_name = body.get('displayName', '').strip()
        
        # Validate input
        errors = {}
        if not email:
            errors['email'] = 'Email is required'
        elif not validate_email(email):
            errors['email'] = 'Invalid email format'
            
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'
            
        if not display_name:
            errors['displayName'] = 'Display name is required'
        elif len(display_name) < 2:
            errors['displayName'] = 'Display name must be at least 2 characters'
        
        if errors:
            return validation_error_response(errors)
        
        # Database operations
        db = get_db_session()
        try:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                return error_response('Email already registered', 409)
            
            # Hash password and create user
            password_hash = hash_password(password)
            
            new_user = User(
                email=email,
                password_hash=password_hash,
                display_name=display_name
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Create JWT token
            token = create_jwt_token(str(new_user.id), new_user.email)
            
            # Return user data and token
            return success_response({
                'user': {
                    'id': str(new_user.id),
                    'email': new_user.email,
                    'displayName': new_user.display_name,
                    'createdAt': new_user.created_at.isoformat() if new_user.created_at else None
                },
                'token': token
            }, 201)
            
        except IntegrityError:
            db.rollback()
            return error_response('Email already registered', 409)
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Signup error: {str(e)}")
        print(f"Signup error type: {type(e)}")
        import traceback
        print(f"Signup traceback: {traceback.format_exc()}")
        return error_response('Signup failed', 500)
