"""
Update user profile (display name and email)
"""

import json
import re
import sys
import os

# Import from layer
sys.path.append('/opt/python/python')
from database import get_db_session, User
from responses import success_response, error_response, validation_error_response
from auth import require_auth, get_user_id_from_event

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@require_auth
def lambda_handler(event, context):
    """Update user profile information"""
    try:
        # Parse request body
        if not event.get('body'):
            return validation_error_response({'body': 'Request body is required'})
        
        body = json.loads(event['body'])
        new_email = body.get('email', '').strip().lower() if body.get('email') else None
        new_display_name = body.get('displayName', '').strip() if body.get('displayName') else None
        
        user_id = get_user_id_from_event(event)
        
        # Validate input
        errors = {}
        
        if new_email is not None:
            if not new_email:
                errors['email'] = 'Email cannot be empty'
            elif not validate_email(new_email):
                errors['email'] = 'Invalid email format'
        
        if new_display_name is not None:
            if not new_display_name:
                errors['displayName'] = 'Display name cannot be empty'
            elif len(new_display_name) < 2:
                errors['displayName'] = 'Display name must be at least 2 characters'
            elif len(new_display_name) > 100:
                errors['displayName'] = 'Display name must be less than 100 characters'
        
        if errors:
            return validation_error_response(errors)
        
        # At least one field must be provided
        if new_email is None and new_display_name is None:
            return validation_error_response({'general': 'At least one field must be updated'})
        
        # Database operations
        db = get_db_session()
        try:
            # Find user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return error_response('User not found', 404)
            
            # Check if email is already taken (if changing email)
            if new_email and new_email != user.email:
                existing_user = db.query(User).filter(User.email == new_email).first()
                if existing_user:
                    return validation_error_response({'email': 'This email is already registered'})
            
            # Update fields
            updated_fields = {}
            
            if new_email and new_email != user.email:
                user.email = new_email
                updated_fields['email'] = user.email
            
            if new_display_name and new_display_name != user.display_name:
                user.display_name = new_display_name
                updated_fields['displayName'] = user.display_name
            
            # If no changes were made
            if not updated_fields:
                return success_response({
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'displayName': user.display_name,
                        'createdAt': user.created_at.isoformat()
                    },
                    'message': 'No changes were made'
                })
            
            db.commit()
            
            # Return updated user data
            return success_response({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'displayName': user.display_name,
                    'createdAt': user.created_at.isoformat()
                },
                'updated': updated_fields,
                'message': 'Profile updated successfully'
            })
            
        finally:
            db.close()
            
    except json.JSONDecodeError:
        return validation_error_response({'body': 'Invalid JSON format'})
    except Exception as e:
        print(f"Profile update error: {str(e)}")
        return error_response('Internal server error', 500)
