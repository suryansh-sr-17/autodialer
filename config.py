import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration management for environment variables"""
    
    # Environment detection
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    TESTING = False
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///autodialer.db'
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'autodialer.db'
    
    # Twilio configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-pro')
    
    # Application configuration
    TEST_MODE = os.environ.get('TEST_MODE', 'True').lower() == 'true'
    MAX_NUMBERS = int(os.environ.get('MAX_NUMBERS', '100'))
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '1048576'))  # 1MB default
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_DIR = os.environ.get('LOG_DIR', 'logs')
    LOG_TO_FILE = os.environ.get('LOG_TO_FILE', 'True').lower() == 'true'
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'False').lower() == 'true'
    CALLS_PER_MINUTE = int(os.environ.get('CALLS_PER_MINUTE', '10'))
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000').split(',')
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration with environment-specific requirements"""
        validation_errors = []
        warnings = []
        
        # Check environment-specific requirements
        if cls.ENVIRONMENT == 'production':
            # Production requires all credentials
            required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER', 'GEMINI_API_KEY']
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            
            if missing_vars:
                validation_errors.append(f"Missing required production environment variables: {', '.join(missing_vars)}")
            
            # Production security checks
            if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
                validation_errors.append("SECRET_KEY must be changed in production")
            
            if cls.DEBUG:
                warnings.append("DEBUG mode is enabled in production")
        
        elif cls.ENVIRONMENT == 'development':
            # Development can work with test credentials
            if not cls.TWILIO_ACCOUNT_SID and not cls.TWILIO_AUTH_TOKEN:
                warnings.append("Twilio credentials not set - call functionality will be disabled")
            
            if not cls.GEMINI_API_KEY:
                warnings.append("Gemini API key not set - AI functionality will be disabled")
        
        # Validate Twilio credentials format if provided
        if cls.TWILIO_ACCOUNT_SID:
            if not cls.TWILIO_ACCOUNT_SID.startswith('AC') or len(cls.TWILIO_ACCOUNT_SID) != 34:
                validation_errors.append("Invalid Twilio Account SID format")
        
        if cls.TWILIO_AUTH_TOKEN:
            if len(cls.TWILIO_AUTH_TOKEN) != 32:
                validation_errors.append("Invalid Twilio Auth Token format")
        
        # Validate phone number format if provided
        if cls.TWILIO_PHONE_NUMBER:
            if not cls.TWILIO_PHONE_NUMBER.startswith('+'):
                validation_errors.append("Twilio phone number must start with + (international format)")
        
        # Validate numeric configurations
        try:
            if cls.MAX_NUMBERS <= 0:
                validation_errors.append("MAX_NUMBERS must be positive")
            if cls.CALLS_PER_MINUTE <= 0:
                validation_errors.append("CALLS_PER_MINUTE must be positive")
        except (ValueError, TypeError):
            validation_errors.append("Numeric configuration values must be valid integers")
        
        # Log validation results
        logger = logging.getLogger(__name__)
        
        if validation_errors:
            for error in validation_errors:
                logger.error(f"Configuration error: {error}")
            raise ValueError(f"Configuration validation failed: {'; '.join(validation_errors)}")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        logger.info(f"Configuration validated successfully for {cls.ENVIRONMENT} environment")
        return True
    
    @classmethod
    def get_config_summary(cls):
        """Get a summary of current configuration (without sensitive data)"""
        return {
            'environment': cls.ENVIRONMENT,
            'debug': cls.DEBUG,
            'test_mode': cls.TEST_MODE,
            'max_numbers': cls.MAX_NUMBERS,
            'log_level': cls.LOG_LEVEL,
            'database_type': 'sqlite' if 'sqlite' in cls.DATABASE_URL.lower() else 'other',
            'twilio_configured': bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN),
            'gemini_configured': bool(cls.GEMINI_API_KEY),
            'rate_limiting': cls.RATE_LIMIT_ENABLED,
            'calls_per_minute': cls.CALLS_PER_MINUTE
        }
    
    @staticmethod
    def get_timestamp():
        """Get current timestamp"""
        return datetime.now().isoformat()

class DevelopmentConfig(Config):
    """Development environment configuration"""
    
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    TEST_MODE = True  # Force test mode in development
    LOG_LEVEL = 'DEBUG'
    
    # Relaxed validation for development
    @classmethod
    def validate_config(cls):
        """Relaxed validation for development"""
        warnings = []
        
        if not cls.TWILIO_ACCOUNT_SID:
            warnings.append("Twilio Account SID not set - using mock mode")
        if not cls.TWILIO_AUTH_TOKEN:
            warnings.append("Twilio Auth Token not set - using mock mode")
        if not cls.TWILIO_PHONE_NUMBER:
            warnings.append("Twilio Phone Number not set - using mock mode")
        if not cls.GEMINI_API_KEY:
            warnings.append("Gemini API Key not set - using fallback mode")
        
        logger = logging.getLogger(__name__)
        for warning in warnings:
            logger.warning(f"Development config: {warning}")
        
        logger.info("Development configuration loaded")
        return True

class TestingConfig(Config):
    """Testing environment configuration"""
    
    DEBUG = False
    TESTING = True
    TEST_MODE = True
    
    # Use in-memory database for testing
    DATABASE_URL = 'sqlite:///:memory:'
    DATABASE_PATH = ':memory:'
    
    # Disable logging to files during testing
    LOG_TO_FILE = False
    LOG_LEVEL = 'WARNING'
    
    # Mock credentials for testing
    TWILIO_ACCOUNT_SID = 'AC' + '0' * 32  # Correct format: AC + 32 chars
    TWILIO_AUTH_TOKEN = '0' * 32          # Correct format: 32 chars
    TWILIO_PHONE_NUMBER = '+18001234567'
    GEMINI_API_KEY = 'test-gemini-key'

class ProductionConfig(Config):
    """Production environment configuration"""
    
    DEBUG = False
    TESTING = False
    TEST_MODE = False  # Disable test mode in production
    
    # Production security
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Must be set
    
    # Production logging
    LOG_LEVEL = 'INFO'
    
    # Enable rate limiting in production
    RATE_LIMIT_ENABLED = True
    
    @classmethod
    def validate_config(cls):
        """Strict validation for production"""
        # Call parent validation first
        super().validate_config()
        
        # Additional production checks
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY must be set to a secure value in production")
        
        if cls.DEBUG:
            raise ValueError("DEBUG must be disabled in production")
        
        if cls.TEST_MODE:
            raise ValueError("TEST_MODE must be disabled in production")
        
        return True

# Configuration factory
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

def get_config(environment=None):
    """Get configuration class based on environment"""
    env = environment or os.environ.get('ENVIRONMENT', 'development').lower()
    return config_map.get(env, DevelopmentConfig)