"""
Comprehensive logging configuration for the Autodialer application
"""

import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
import json

class AutodialerFormatter(logging.Formatter):
    """Custom formatter for Autodialer logs with structured output"""
    
    def __init__(self, include_extra=True):
        self.include_extra = include_extra
        super().__init__()
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'lineno', 
                              'funcName', 'created', 'msecs', 'relativeCreated', 
                              'thread', 'threadName', 'processName', 'process',
                              'exc_info', 'exc_text', 'stack_info', 'getMessage']:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry['extra'] = extra_fields
        
        return json.dumps(log_entry, default=str)

class CallLogFilter(logging.Filter):
    """Filter for call-related logs"""
    
    def filter(self, record):
        # Only pass through call-related logs
        call_keywords = ['call', 'twilio', 'phone', 'dial', 'sms']
        message = record.getMessage().lower()
        return any(keyword in message for keyword in call_keywords)

class ErrorLogFilter(logging.Filter):
    """Filter for error and warning logs"""
    
    def filter(self, record):
        return record.levelno >= logging.WARNING

class DebugLogFilter(logging.Filter):
    """Filter for debug logs (only in debug mode)"""
    
    def __init__(self, debug_mode=False):
        super().__init__()
        self.debug_mode = debug_mode
    
    def filter(self, record):
        if not self.debug_mode:
            return record.levelno >= logging.INFO
        return True

class LoggingManager:
    """Centralized logging management for the Autodialer application"""
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_dir: str = "logs",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 debug_mode: bool = False):
        
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = log_dir
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.debug_mode = debug_mode
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configure logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up comprehensive logging configuration"""
        
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
        
        # Set root logger level
        logging.getLogger().setLevel(self.log_level)
        
        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        
        json_formatter = AutodialerFormatter(include_extra=True)
        
        # Console handler (for development)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO if not self.debug_mode else logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(DebugLogFilter(self.debug_mode))
        
        # Main application log file (rotating)
        app_log_file = os.path.join(self.log_dir, 'autodialer.log')
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(file_formatter)
        
        # Error log file (errors and warnings only)
        error_log_file = os.path.join(self.log_dir, 'errors.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(file_formatter)
        error_handler.addFilter(ErrorLogFilter())
        
        # Call log file (call-related logs only)
        call_log_file = os.path.join(self.log_dir, 'calls.log')
        call_handler = logging.handlers.RotatingFileHandler(
            call_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        call_handler.setLevel(logging.INFO)
        call_handler.setFormatter(file_formatter)
        call_handler.addFilter(CallLogFilter())
        
        # JSON log file (structured logs for analysis)
        json_log_file = os.path.join(self.log_dir, 'autodialer.json')
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(json_formatter)
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(call_handler)
        root_logger.addHandler(json_handler)
        
        # Configure specific loggers
        self._configure_specific_loggers()
        
        logging.info("Logging system initialized successfully")
        logging.info(f"Log level: {logging.getLevelName(self.log_level)}")
        logging.info(f"Log directory: {self.log_dir}")
        logging.info(f"Debug mode: {self.debug_mode}")
    
    def _configure_specific_loggers(self):
        """Configure loggers for specific modules"""
        
        # Twilio logger (reduce verbosity)
        twilio_logger = logging.getLogger('twilio')
        twilio_logger.setLevel(logging.WARNING)
        
        # HTTP requests logger (reduce verbosity)
        requests_logger = logging.getLogger('urllib3')
        requests_logger.setLevel(logging.WARNING)
        
        # Flask logger
        flask_logger = logging.getLogger('werkzeug')
        flask_logger.setLevel(logging.WARNING if not self.debug_mode else logging.INFO)
        
        # Database logger
        db_logger = logging.getLogger('sqlite3')
        db_logger.setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        return logging.getLogger(name)
    
    def log_call_attempt(self, phone_number: str, call_sid: Optional[str] = None, 
                        status: str = "initiated", details: Dict[str, Any] = None):
        """Log a call attempt with structured data"""
        logger = self.get_logger('autodialer.calls')
        
        log_data = {
            'phone_number': phone_number,
            'call_sid': call_sid,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f"Call {status}: {phone_number}", extra=log_data)
    
    def log_error_with_context(self, error: Exception, operation: str, 
                              context: Dict[str, Any] = None):
        """Log an error with additional context"""
        logger = self.get_logger('autodialer.errors')
        
        error_data = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        
        if context:
            error_data['context'] = context
        
        logger.error(f"Error in {operation}: {error}", extra=error_data, exc_info=True)
    
    def log_performance_metric(self, operation: str, duration: float, 
                              details: Dict[str, Any] = None):
        """Log performance metrics"""
        logger = self.get_logger('autodialer.performance')
        
        perf_data = {
            'operation': operation,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            perf_data.update(details)
        
        logger.info(f"Performance: {operation} took {duration:.3f}s", extra=perf_data)
    
    def log_user_action(self, action: str, user_input: str = None, 
                       result: Dict[str, Any] = None):
        """Log user actions for audit trail"""
        logger = self.get_logger('autodialer.audit')
        
        audit_data = {
            'action': action,
            'user_input': user_input,
            'result_status': result.get('status') if result else None,
            'timestamp': datetime.now().isoformat()
        }
        
        if result:
            audit_data['result'] = result
        
        logger.info(f"User action: {action}", extra=audit_data)
    
    def log_system_event(self, event: str, details: Dict[str, Any] = None):
        """Log system events"""
        logger = self.get_logger('autodialer.system')
        
        event_data = {
            'event': event,
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            event_data.update(details)
        
        logger.info(f"System event: {event}", extra=event_data)
    
    def set_debug_mode(self, debug: bool):
        """Enable or disable debug mode"""
        self.debug_mode = debug
        
        # Update console handler
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(logging.DEBUG if debug else logging.INFO)
                # Update filter
                handler.filters.clear()
                handler.addFilter(DebugLogFilter(debug))
        
        logging.info(f"Debug mode {'enabled' if debug else 'disabled'}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        stats = {
            'log_directory': self.log_dir,
            'log_level': logging.getLevelName(self.log_level),
            'debug_mode': self.debug_mode,
            'log_files': []
        }
        
        # Get log file information
        if os.path.exists(self.log_dir):
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log') or filename.endswith('.json'):
                    filepath = os.path.join(self.log_dir, filename)
                    if os.path.isfile(filepath):
                        file_stats = os.stat(filepath)
                        stats['log_files'].append({
                            'name': filename,
                            'size_bytes': file_stats.st_size,
                            'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                        })
        
        return stats

# Global logging manager instance
logging_manager = None

def initialize_logging(log_level: str = "INFO", 
                      log_dir: str = "logs",
                      debug_mode: bool = False) -> LoggingManager:
    """Initialize the global logging manager"""
    global logging_manager
    
    logging_manager = LoggingManager(
        log_level=log_level,
        log_dir=log_dir,
        debug_mode=debug_mode
    )
    
    return logging_manager

def get_logging_manager() -> Optional[LoggingManager]:
    """Get the global logging manager instance"""
    return logging_manager

# Convenience functions for common logging operations
def log_call_attempt(phone_number: str, call_sid: Optional[str] = None, 
                    status: str = "initiated", **kwargs):
    """Convenience function to log call attempts"""
    if logging_manager:
        logging_manager.log_call_attempt(phone_number, call_sid, status, kwargs)

def log_error_with_context(error: Exception, operation: str, **context):
    """Convenience function to log errors with context"""
    if logging_manager:
        logging_manager.log_error_with_context(error, operation, context)

def log_performance_metric(operation: str, duration: float, **details):
    """Convenience function to log performance metrics"""
    if logging_manager:
        logging_manager.log_performance_metric(operation, duration, details)

def log_user_action(action: str, user_input: str = None, result: Dict[str, Any] = None):
    """Convenience function to log user actions"""
    if logging_manager:
        logging_manager.log_user_action(action, user_input, result)

def log_system_event(event: str, **details):
    """Convenience function to log system events"""
    if logging_manager:
        logging_manager.log_system_event(event, details)

# Decorator for automatic performance logging
def log_performance(operation_name: str = None):
    """Decorator to automatically log function performance"""
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance_metric(operation, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_performance_metric(operation, duration, success=False, error=str(e))
                raise
        
        return wrapper
    return decorator

# Context manager for operation logging
class LoggedOperation:
    """Context manager for logging operations with automatic timing"""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time = None
        self.logger = logging.getLogger('autodialer.operations')
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed operation: {self.operation} in {duration:.3f}s", 
                           extra={**self.context, 'duration': duration, 'success': True})
            log_performance_metric(self.operation, duration, **self.context)
        else:
            self.logger.error(f"Failed operation: {self.operation} after {duration:.3f}s: {exc_val}", 
                            extra={**self.context, 'duration': duration, 'success': False, 'error': str(exc_val)})
            log_performance_metric(self.operation, duration, success=False, error=str(exc_val), **self.context)