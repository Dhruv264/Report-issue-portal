import os

class Config:
    """Flask application configuration"""
    
    # Secret key for session management (change this in production!)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    DB_HOST = 'localhost'
    DB_NAME = 'flask_auth_db'
    DB_USER = 'postgres'
    DB_PASSWORD = 'astha'
    DB_PORT = '5432'
    
    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour in seconds
