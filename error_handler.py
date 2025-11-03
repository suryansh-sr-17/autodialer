"""
Comprehensive error handling module for the Autodialer application
"""

import logging
import traceback
import functools
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
import sqlite3
from twilio.base.exceptions import TwilioException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutodialerError(Exception):
    """Base exception class for Autodialer application"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code or "AUTODIALER_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }

class DatabaseError(AutodialerError):
    """Database-related errors"""
    
    def __init__(self, message: str, operation: str = None, details: Dict = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={**(details or {}), "operation": operation}
        )

class TwilioAPIError(AutodialerError):
    """Twilio API-related errors"""
    
    def __init__(self, message: str, twilio_error: TwilioException = None, details: Dict = None):
        error_details = details or {}
        if twilio_error:
            error_details.update({
                "twilio_code": getattr(twilio_error, 'code', None),
                "twilio_status": getattr(twilio_error, 'status', None),
                "twilio_uri": getattr(twilio_error, 'uri', None)
            })
        
        super().__init__(
            message=message,
            error_code="TWILIO_API_ERROR",
            details=error_details
        )

class ValidationError(AutodialerError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, details: Dict = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details
        )

class AIProcessingError(AutodialerError):
    """AI processing and Gemini API errors"""
    
    def __init__(self, message: str, ai_service: str = None, details: Dict = None):
        error_details = details or {}
        if ai_service:
            error_details["ai_service"] = ai_service
        
        super().__init__(
            message=message,
            error_code="AI_PROCESSING_ERROR",
            details=error_details
        )

class ConfigurationError(AutodialerError):
    """Configuration and environment errors"""
    
    def __init__(self, message: str, config_key: str = None, details: Dict = None):
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=error_details
        )

class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self, log_to_file: bool = True, log_file: str = "autodialer_errors.log"):
        self.log_to_file = log_to_file
        self.log_file = log_file
        
        if log_to_file:
            # Set up file logging
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.ERROR)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    def handle_database_error(self, error: Exception, operation: str = None, 
                            context: Dict = None) -> DatabaseError:
        """Handle database-related errors"""
        if isinstance(error, sqlite3.IntegrityError):
            message = f"Database integrity error: {str(error)}"
            if "UNIQUE constraint failed" in str(error):
                message = "Duplicate entry detected"
        elif isinstance(error, sqlite3.OperationalError):
            message = f"Database operation failed: {str(error)}"
        elif isinstance(error, sqlite3.DatabaseError):
            message = f"Database error: {str(error)}"
        else:
            message = f"Unexpected database error: {str(error)}"
        
        db_error = DatabaseError(
            message=message,
            operation=operation,
            details={
                "original_error": str(error),
                "error_type": type(error).__name__,
                "context": context or {}
            }
        )
        
        logger.error(f"Database Error - Operation: {operation}, Error: {message}")
        if context:
            logger.error(f"Context: {context}")
        
        return db_error
    
    def handle_twilio_error(self, error: TwilioException, operation: str = None,
                          phone_number: str = None) -> TwilioAPIError:
        """Handle Twilio API errors"""
        error_code = getattr(error, 'code', None)
        
        # Map common Twilio errors to user-friendly messages
        error_messages = {
            20003: "Authentication failed - check Twilio credentials",
            21211: "Invalid phone number format",
            21212: "Phone number not reachable",
            21214: "Invalid phone number - not a mobile number",
            21408: "Permission denied - check account permissions",
            21610: "Phone number is blocked or invalid",
            30001: "Message queue is full - try again later",
            30002: "Account suspended",
            30003: "Unreachable destination",
            30004: "Message blocked by carrier",
            30005: "Unknown destination",
            30006: "Landline or unreachable carrier"
        }
        
        if error_code in error_messages:
            message = error_messages[error_code]
        else:
            message = f"Twilio API error: {str(error)}"
        
        twilio_error = TwilioAPIError(
            message=message,
            twilio_error=error,
            details={
                "operation": operation,
                "phone_number": phone_number,
                "original_error": str(error)
            }
        )
        
        logger.error(f"Twilio Error - Code: {error_code}, Operation: {operation}, "
                    f"Phone: {phone_number}, Message: {message}")
        
        return twilio_error
    
    def handle_validation_error(self, message: str, field: str = None, 
                              value: Any = None) -> ValidationError:
        """Handle input validation errors"""
        validation_error = ValidationError(
            message=message,
            field=field,
            value=value
        )
        
        logger.warning(f"Validation Error - Field: {field}, Value: {value}, "
                      f"Message: {message}")
        
        return validation_error
    
    def handle_ai_error(self, error: Exception, ai_service: str = None,
                       user_input: str = None) -> AIProcessingError:
        """Handle AI processing errors"""
        if "API key" in str(error).lower():
            message = "AI service authentication failed - check API key"
        elif "quota" in str(error).lower() or "limit" in str(error).lower():
            message = "AI service quota exceeded - try again later"
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            message = "AI service connection failed - check internet connection"
        else:
            message = f"AI processing error: {str(error)}"
        
        ai_error = AIProcessingError(
            message=message,
            ai_service=ai_service,
            details={
                "original_error": str(error),
                "error_type": type(error).__name__,
                "user_input": user_input
            }
        )
        
        logger.error(f"AI Error - Service: {ai_service}, Input: {user_input}, "
                    f"Message: {message}")
        
        return ai_error
    
    def handle_configuration_error(self, message: str, config_key: str = None) -> ConfigurationError:
        """Handle configuration errors"""
        config_error = ConfigurationError(
            message=message,
            config_key=config_key
        )
        
        logger.error(f"Configuration Error - Key: {config_key}, Message: {message}")
        
        return config_error
    
    def handle_generic_error(self, error: Exception, operation: str = None,
                           context: Dict = None) -> AutodialerError:
        """Handle generic/unexpected errors"""
        message = f"Unexpected error in {operation or 'operation'}: {str(error)}"
        
        generic_error = AutodialerError(
            message=message,
            error_code="GENERIC_ERROR",
            details={
                "operation": operation,
                "original_error": str(error),
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc(),
                "context": context or {}
            }
        )
        
        logger.error(f"Generic Error - Operation: {operation}, Error: {message}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return generic_error

# Global error handler instance
error_handler = ErrorHandler()

def handle_errors(operation: str = None, return_dict: bool = True):
    """
    Decorator for automatic error handling
    
    Args:
        operation (str): Description of the operation being performed
        return_dict (bool): Whether to return error as dict or raise exception
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AutodialerError as e:
                # Re-raise custom errors
                if return_dict:
                    return {
                        "status": "error",
                        **e.to_dict()
                    }
                else:
                    raise
            except sqlite3.Error as e:
                db_error = error_handler.handle_database_error(e, operation)
                if return_dict:
                    return {
                        "status": "error",
                        **db_error.to_dict()
                    }
                else:
                    raise db_error
            except TwilioException as e:
                twilio_error = error_handler.handle_twilio_error(e, operation)
                if return_dict:
                    return {
                        "status": "error",
                        **twilio_error.to_dict()
                    }
                else:
                    raise twilio_error
            except Exception as e:
                generic_error = error_handler.handle_generic_error(e, operation)
                if return_dict:
                    return {
                        "status": "error",
                        **generic_error.to_dict()
                    }
                else:
                    raise generic_error
        
        return wrapper
    return decorator

def safe_execute(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Function arguments
        **kwargs: Function keyword arguments
    
    Returns:
        dict: Result with status and error information
    """
    try:
        result = func(*args, **kwargs)
        if isinstance(result, dict) and "status" in result:
            return result
        else:
            return {
                "status": "success",
                "result": result
            }
    except AutodialerError as e:
        return {
            "status": "error",
            **e.to_dict()
        }
    except Exception as e:
        generic_error = error_handler.handle_generic_error(e, func.__name__)
        return {
            "status": "error",
            **generic_error.to_dict()
        }

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required fields are present in data
    
    Args:
        data (dict): Data to validate
        required_fields (list): List of required field names
    
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )

def validate_phone_number_format(phone_number: str) -> str:
    """
    Validate and format phone number
    
    Args:
        phone_number (str): Phone number to validate
    
    Returns:
        str: Formatted phone number
    
    Raises:
        ValidationError: If phone number is invalid
    """
    from models import validate_phone_number
    
    if not phone_number or not isinstance(phone_number, str):
        raise ValidationError(
            message="Phone number must be a non-empty string",
            field="phone_number",
            value=phone_number
        )
    
    is_valid, result = validate_phone_number(phone_number)
    if not is_valid:
        raise ValidationError(
            message=f"Invalid phone number format: {result}",
            field="phone_number",
            value=phone_number
        )
    
    return result

def log_error_context(operation: str, context: Dict[str, Any]) -> None:
    """
    Log error context for debugging
    
    Args:
        operation (str): Operation being performed
        context (dict): Context information
    """
    logger.error(f"Error Context - Operation: {operation}")
    for key, value in context.items():
        logger.error(f"  {key}: {value}")

def create_error_response(error: Union[Exception, AutodialerError], 
                         operation: str = None) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error: Exception or AutodialerError
        operation: Operation description
    
    Returns:
        dict: Standardized error response
    """
    if isinstance(error, AutodialerError):
        return {
            "status": "error",
            **error.to_dict()
        }
    else:
        generic_error = error_handler.handle_generic_error(error, operation)
        return {
            "status": "error",
            **generic_error.to_dict()
        }

def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if an error is recoverable (temporary)
    
    Args:
        error: Exception to check
    
    Returns:
        bool: True if error might be temporary/recoverable
    """
    recoverable_patterns = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "rate limit",
        "quota",
        "busy",
        "unavailable"
    ]
    
    error_str = str(error).lower()
    return any(pattern in error_str for pattern in recoverable_patterns)

def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """
    Calculate exponential backoff delay for retries
    
    Args:
        attempt (int): Attempt number (starting from 1)
        base_delay (float): Base delay in seconds
        max_delay (float): Maximum delay in seconds
    
    Returns:
        float: Delay in seconds
    """
    import random
    
    delay = base_delay * (2 ** (attempt - 1))
    delay = min(delay, max_delay)
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0.1, 0.3) * delay
    return delay + jitter