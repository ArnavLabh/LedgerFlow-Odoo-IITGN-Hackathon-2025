import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # JWT
    JWT_SECRET = os.environ.get('JWT_SECRET') or 'dev-jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = 15 * 60  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES = 30 * 24 * 60 * 60  # 30 days
    
    # Database
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        # Fallback to SQLite for local development
        database_url = 'sqlite:///ledgerflow.db'
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configure engine options based on database type
    if database_url.startswith('postgresql'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'connect_timeout': 10,
                'application_name': 'ledgerflow'
            }
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }
    
    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    OAUTH_REDIRECT_URI = os.environ.get('OAUTH_REDIRECT_URI') or 'http://localhost:5000/api/auth/oauth/google/callback'
    
    # CORS
    FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN') or 'http://localhost:5000'
    
    # Platform
    PLATFORM = os.environ.get('PLATFORM') or 'local'
    
    # Default Currency
    DEFAULT_CURRENCY = 'INR'
    
    # Sentry (optional)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')