"""
Serverless-compatible configuration for Vercel deployment
"""

import os
from datetime import datetime

class Config:
    """Serverless configuration management"""
    
    # Environment detection
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production').lower()
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False  # Always False in serverless
    TESTING = False
    
    # Database configuration (use in-memory for serverless)
    DATABASE_URL = 'sqlite:///:memory:'
    DATABASE_PATH = ':memory:'
    
    # Twilio configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-pro')
    
    # Application configuration
    TEST_MODE = os.environ.get('TEST_MODE', 'False').lower() == 'true'
    MAX_NUMBERS = int(os.environ.get('MAX_NUMBERS', '100'))
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '1048576'))  # 1MB default
    
    # Logging configuration (simplified for serverless)
    LOG_LEVEL = 'INFO'
    LOG_TO_FILE = False  # No file logging in serverless
    
    # Rate limiting
    RATE_LIMIT_ENABLED = False  # Disabled in serverless
    CALLS_PER_MINUTE = int(os.environ.get('CALLS_PER_MINUTE', '10'))
    
    @classmethod
    def validate_config(cls):
        """Basic validation for serverless environment"""
        missing_vars = []
        
        # Check required environment variables
        required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER', 'GEMINI_API_KEY']
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    @classmethod
    def get_config_summary(cls):
        """Get configuration summary"""
        return {
            'environment': cls.ENVIRONMENT,
            'test_mode': cls.TEST_MODE,
            'max_numbers': cls.MAX_NUMBERS,
            'twilio_configured': bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN),
            'gemini_configured': bool(cls.GEMINI_API_KEY)
        }
    
    @staticmethod
    def get_timestamp():
        """Get current timestamp"""
        return datetime.now().isoformat()