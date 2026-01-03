"""
AWS Parameter Store utility for Pick6 application
"""
import os
import boto3
from functools import lru_cache

# Initialize SSM client
ssm = boto3.client('ssm')

@lru_cache(maxsize=128)
def get_parameter(parameter_name: str, decrypt: bool = True) -> str:
    """
    Retrieve a parameter from AWS Systems Manager Parameter Store.
    
    Args:
        parameter_name: The name of the parameter to retrieve
        decrypt: Whether to decrypt SecureString parameters
    
    Returns:
        The parameter value as a string
    
    Raises:
        Exception: If parameter cannot be retrieved
    """
    try:
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=decrypt
        )
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Error retrieving parameter {parameter_name}: {str(e)}")
        raise

def get_jwt_secret() -> str:
    """Get JWT secret from Parameter Store."""
    parameter_name = os.environ.get('JWT_SECRET_PARAMETER')
    if not parameter_name:
        raise ValueError("JWT_SECRET_PARAMETER environment variable not set")
    return get_parameter(parameter_name)

def get_cfb_api_key() -> str:
    """Get CollegeFootballData.com API key from Parameter Store."""
    parameter_name = os.environ.get('CFB_API_KEY_PARAMETER')
    if not parameter_name:
        raise ValueError("CFB_API_KEY_PARAMETER environment variable not set")
    return get_parameter(parameter_name)

def get_database_url() -> str:
    """Get database URL from environment variable (will be Neon connection string)."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return database_url

# For backward compatibility, expose the secrets as environment-like variables
def get_env_with_secrets():
    """
    Get environment variables with secrets loaded from Parameter Store.
    Use this to maintain compatibility with existing code.
    """
    return {
        'JWT_SECRET': get_jwt_secret(),
        'CFB_API_KEY': get_cfb_api_key(),
        'DATABASE_URL': get_database_url(),
        'ENVIRONMENT': os.environ.get('ENVIRONMENT', 'dev')
    }
