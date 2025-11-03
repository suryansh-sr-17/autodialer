from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import logging
import traceback
from config import Config
from models import (
    init_db, 
    get_all_phone_numbers, 
    add_phone_number, 
    remove_phone_number,
    clear_all_phone_numbers,
    get_phone_number_count
)
from call_manager import CallManager
from command_handlers import CommandExecutionHandler
from error_handler import (
    AutodialerError,
    DatabaseError,
    TwilioAPIError,
    ValidationError,
    ConfigurationError,
    AIProcessingError,
    error_handler,
    handle_errors,
    create_error_response,
    validate_required_fields
)

# Initialize comprehensive logging
from logging_config import (
    initialize_logging, 
    log_call_attempt, 
    log_error_with_context,
    log_user_action,
    log_system_event,
    LoggedOperation
)

# Set up logging system
debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
log_level = os.getenv('LOG_LEVEL', 'INFO')

logging_manager = initialize_logging(
    log_level=log_level,
    log_dir='logs',
    debug_mode=debug_mode
)

logger = logging.getLogger(__name__)
logger.info("Application logging initialized")

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend integration
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5000'])

# Initialize database with error handling
try:
    with LoggedOperation("database_initialization"):
        init_db()
    log_system_event("database_initialized", status="success")
except Exception as e:
    logger.critical(f"Database initialization failed: {e}")
    log_error_with_context(e, "database_initialization")
    log_system_event("database_initialization_failed", error=str(e))
    # Continue running but log the error - some endpoints might still work

# Initialize CallManager with comprehensive error handling
call_manager = None
call_manager_error = None
try:
    with LoggedOperation("call_manager_initialization"):
        call_manager = CallManager()
    log_system_event("call_manager_initialized", status="success")
except ConfigurationError as e:
    call_manager_error = f"Configuration error: {e.message}"
    log_error_with_context(e, "call_manager_initialization")
    log_system_event("call_manager_initialization_failed", error_type="configuration", error=e.message)
except TwilioAPIError as e:
    call_manager_error = f"Twilio API error: {e.message}"
    log_error_with_context(e, "call_manager_initialization")
    log_system_event("call_manager_initialization_failed", error_type="twilio_api", error=e.message)
except Exception as e:
    call_manager_error = f"Unexpected error: {str(e)}"
    log_error_with_context(e, "call_manager_initialization")
    log_system_event("call_manager_initialization_failed", error_type="unexpected", error=str(e))

# Initialize Command Handler with error handling
command_handler = None
command_handler_error = None
try:
    with LoggedOperation("command_handler_initialization"):
        command_handler = CommandExecutionHandler()
    log_system_event("command_handler_initialized", status="success")
except ConfigurationError as e:
    command_handler_error = f"Configuration error: {e.message}"
    log_error_with_context(e, "command_handler_initialization")
    log_system_event("command_handler_initialization_failed", error_type="configuration", error=e.message)
except AIProcessingError as e:
    command_handler_error = f"AI processing error: {e.message}"
    log_error_with_context(e, "command_handler_initialization")
    log_system_event("command_handler_initialization_failed", error_type="ai_processing", error=e.message)
except Exception as e:
    command_handler_error = f"Unexpected error: {str(e)}"
    log_error_with_context(e, "command_handler_initialization")
    log_system_event("command_handler_initialization_failed", error_type="unexpected", error=str(e))

# Log initialization summary
logger.info(f"Application initialization complete:")
logger.info(f"  - CallManager: {'OK' if call_manager else 'FAIL'} {call_manager_error or ''}")
logger.info(f"  - CommandHandler: {'OK' if command_handler else 'FAIL'} {command_handler_error or ''}")

# Comprehensive error handlers
@app.errorhandler(AutodialerError)
def handle_autodialer_error(error):
    """Handle custom Autodialer errors"""
    logger.error(f"Autodialer error: {error.message}")
    return jsonify(error.to_dict()), 400

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle validation errors"""
    logger.warning(f"Validation error: {error.message}")
    return jsonify(error.to_dict()), 400

@app.errorhandler(DatabaseError)
def handle_database_error(error):
    """Handle database errors"""
    logger.error(f"Database error: {error.message}")
    return jsonify(error.to_dict()), 500

@app.errorhandler(TwilioAPIError)
def handle_twilio_error(error):
    """Handle Twilio API errors"""
    logger.error(f"Twilio error: {error.message}")
    return jsonify(error.to_dict()), 502

@app.errorhandler(ConfigurationError)
def handle_config_error(error):
    """Handle configuration errors"""
    logger.error(f"Configuration error: {error.message}")
    return jsonify(error.to_dict()), 500

@app.errorhandler(AIProcessingError)
def handle_ai_error(error):
    """Handle AI processing errors"""
    logger.error(f"AI processing error: {error.message}")
    return jsonify(error.to_dict()), 502

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "error_code": "NOT_FOUND",
        "requested_url": request.url
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    logger.warning(f"405 error: {request.method} {request.url}")
    return jsonify({
        "status": "error",
        "message": f"Method {request.method} not allowed for this endpoint",
        "error_code": "METHOD_NOT_ALLOWED",
        "allowed_methods": error.description
    }), 405

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle request too large errors"""
    logger.warning(f"413 error: Request too large")
    return jsonify({
        "status": "error",
        "message": "Request entity too large",
        "error_code": "REQUEST_TOO_LARGE"
    }), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "error_code": "INTERNAL_ERROR",
        "details": "An unexpected error occurred. Please try again."
    }), 500

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle any unexpected errors"""
    logger.error(f"Unexpected error: {error}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Don't expose internal error details in production
    if app.debug:
        error_details = str(error)
    else:
        error_details = "An unexpected error occurred"
    
    return jsonify({
        "status": "error",
        "message": error_details,
        "error_code": "UNEXPECTED_ERROR"
    }), 500

@app.route('/')
def index():
    """Main interface page"""
    try:
        # Get basic system info for the template
        system_info = {
            "call_manager_available": call_manager is not None,
            "command_handler_available": command_handler is not None,
            "phone_count": get_phone_number_count()
        }
        
        return render_template('index.html', system_info=system_info)
        
    except Exception as e:
        logger.error(f"Error loading main page: {e}")
        # Fallback to basic template
        return render_template('index.html', system_info={
            "call_manager_available": False,
            "command_handler_available": False,
            "phone_count": 0
        })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": Config.get_timestamp(),
            "components": {
                "database": "unknown",
                "call_manager": "not_initialized",
                "command_handler": "not_initialized"
            }
        }
        
        # Check database
        try:
            count = get_phone_number_count()
            health_status["components"]["database"] = "operational"
        except Exception as e:
            health_status["components"]["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Call Manager
        if call_manager:
            try:
                cm_test = call_manager.test_connection()
                health_status["components"]["call_manager"] = cm_test.get("status", "failed")
            except Exception as e:
                health_status["components"]["call_manager"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        
        # Check Command Handler
        if command_handler:
            try:
                ch_test = command_handler.test_system()
                overall_status = ch_test.get("test_results", {}).get("overall_status", "failed")
                health_status["components"]["command_handler"] = overall_status
            except Exception as e:
                health_status["components"]["command_handler"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        
        # Determine overall status
        if health_status["components"]["database"] != "operational":
            health_status["status"] = "unhealthy"
        elif not call_manager and not command_handler:
            health_status["status"] = "unhealthy"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

@app.route('/upload-numbers', methods=['POST'])
@handle_errors(operation="upload_numbers")
def upload_numbers():
    """Handle number uploads/paste with comprehensive error handling"""
    # Check if command handler is available
    if not command_handler:
        error_msg = command_handler_error or "Command Handler not initialized"
        raise ConfigurationError(
            message=f"Command Handler unavailable: {error_msg}",
            config_key="command_handler"
        )
    
    # Validate request content type
    if not request.is_json:
        raise ValidationError(
            message="Request must be JSON",
            field="content_type",
            value=request.content_type
        )
    
    # Get and validate request data
    data = request.get_json()
    if not data:
        raise ValidationError(
            message="Request body is empty or invalid JSON",
            field="request_body"
        )
    
    # Validate required fields
    validate_required_fields(data, ['numbers'])
    
    numbers_input = data.get('numbers')
    
    # Validate numbers input
    if not isinstance(numbers_input, (str, list)):
        raise ValidationError(
            message="Numbers must be a string or list",
            field="numbers",
            value=type(numbers_input).__name__
        )
    
    # Convert list to string if needed
    if isinstance(numbers_input, list):
        numbers_text = '\n'.join(str(num) for num in numbers_input)
    else:
        numbers_text = str(numbers_input).strip()
    
    if not numbers_text:
        raise ValidationError(
            message="Numbers input cannot be empty",
            field="numbers",
            value=numbers_text
        )
    
    # Check input length (prevent abuse)
    if len(numbers_text) > 100000:  # 100KB limit
        raise ValidationError(
            message="Numbers input too large (max 100KB)",
            field="numbers",
            value=f"{len(numbers_text)} characters"
        )
    
    logger.info(f"Processing bulk number input: {len(numbers_text)} characters")
    
    # Log user action
    log_user_action("upload_numbers", numbers_text[:100] + "..." if len(numbers_text) > 100 else numbers_text)
    
    # Process bulk number input
    try:
        with LoggedOperation("process_bulk_numbers", input_length=len(numbers_text)):
            result = command_handler.process_bulk_number_input(numbers_text)
        
        # Ensure result has proper format
        if not isinstance(result, dict):
            raise AIProcessingError(
                message="Invalid response from command handler",
                details={"response_type": type(result).__name__}
            )
        
        # Log the result
        log_user_action("upload_numbers_completed", result=result)
        logger.info(f"Bulk number processing completed: {result.get('status', 'unknown')}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in bulk number processing: {e}")
        if isinstance(e, (AutodialerError, ValidationError, DatabaseError)):
            raise  # Re-raise our custom errors
        else:
            raise AIProcessingError(
                message=f"Failed to process numbers: {str(e)}",
                details={"error_type": type(e).__name__}
            )

@app.route('/ai-command', methods=['POST'])
def ai_command():
    """Process AI prompt commands"""
    if not command_handler:
        return jsonify({
            "status": "error",
            "message": "AI Command Handler not initialized. Check API credentials."
        }), 500
    
    try:
        data = request.get_json()
        if not data or not data.get('command'):
            return jsonify({
                "status": "error",
                "message": "No command provided"
            }), 400
        
        user_command = data.get('command', '').strip()
        
        if not user_command:
            return jsonify({
                "status": "error",
                "message": "Empty command provided"
            }), 400
        
        # Process the command
        result = command_handler.process_and_execute_command(user_command)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error processing AI command: {str(e)}"
        }), 500

@app.route('/call-logs')
def call_logs():
    """Retrieve call history"""
    if not call_manager:
        return jsonify({
            "status": "error",
            "message": "CallManager not initialized"
        }), 500
    
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        phone_number = request.args.get('phone_number')
        status = request.args.get('status')
        
        # Get call logs
        result = call_manager.get_recent_call_logs(
            limit=limit,
            phone_number=phone_number,
            status=status
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving call logs: {str(e)}"
        }), 500

@app.route('/call-statistics')
def call_statistics():
    """Get call statistics"""
    if not call_manager:
        return jsonify({
            "status": "error",
            "message": "CallManager not initialized"
        }), 500
    
    try:
        # Get query parameters
        phone_number = request.args.get('phone_number')
        days = request.args.get('days', type=int)
        
        # Get statistics
        result = call_manager.get_call_statistics_summary(
            phone_number=phone_number,
            days=days
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error retrieving statistics: {str(e)}"
        }), 500

@app.route('/system-status')
def system_status():
    """Get system status and component health"""
    try:
        status = {
            "call_manager": "not_initialized",
            "command_handler": "not_initialized",
            "database": "unknown"
        }
        
        # Check Call Manager
        if call_manager:
            cm_test = call_manager.test_connection()
            status["call_manager"] = cm_test.get("status", "failed")
        
        # Check Command Handler
        if command_handler:
            ch_test = command_handler.test_system()
            status["command_handler"] = ch_test.get("test_results", {}).get("overall_status", "failed")
        
        # Check Database (simple check)
        try:
            from models import get_phone_number_count
            count = get_phone_number_count()
            status["database"] = "operational"
            status["phone_numbers_count"] = count
        except Exception as e:
            status["database"] = f"error: {str(e)}"
        
        return jsonify({
            "status": "success",
            "system_status": status
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error checking system status: {str(e)}"
        }), 500

@app.route('/numbers', methods=['GET'])
@app.route('/get-numbers', methods=['GET'])
def get_numbers():
    """Get all phone numbers"""
    try:
        numbers = get_all_phone_numbers()
        count = get_phone_number_count()
        
        return jsonify({
            "status": "success",
            "numbers": numbers,
            "count": count
        })
        
    except Exception as e:
        logger.error(f"Error retrieving numbers: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving numbers: {str(e)}"
        }), 500

@app.route('/numbers', methods=['POST'])
def add_number():
    """Add a single phone number"""
    try:
        data = request.get_json()
        if not data or not data.get('number'):
            return jsonify({
                "status": "error",
                "message": "Phone number is required"
            }), 400
        
        phone_number = data.get('number', '').strip()
        
        if not phone_number:
            return jsonify({
                "status": "error",
                "message": "Empty phone number provided"
            }), 400
        
        # Add the number
        add_result = add_phone_number(phone_number)
        
        if add_result.get('status') == 'success':
            return jsonify({
                "status": "success",
                "message": add_result.get('message', 'Number added successfully'),
                "number": phone_number
            })
        else:
            return jsonify({
                "status": "error",
                "message": add_result.get('message', 'Failed to add number'),
                "number": phone_number
            }), 400
        
    except Exception as e:
        logger.error(f"Error adding number: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error adding number: {str(e)}"
        }), 500

@app.route('/numbers/<path:number>', methods=['DELETE'])
def delete_number(number):
    """Delete a specific phone number"""
    try:
        if not number:
            return jsonify({
                "status": "error",
                "message": "Phone number is required"
            }), 400
        
        # Remove the number
        success, message = remove_phone_number(number)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message,
                "number": number
            })
        else:
            return jsonify({
                "status": "error",
                "message": message,
                "number": number
            }), 400
        
    except Exception as e:
        logger.error(f"Error deleting number: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error deleting number: {str(e)}"
        }), 500

@app.route('/numbers', methods=['DELETE'])
def clear_numbers():
    """Clear all phone numbers"""
    try:
        success, message = clear_all_phone_numbers()
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            })
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 500
        
    except Exception as e:
        logger.error(f"Error clearing numbers: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error clearing numbers: {str(e)}"
        }), 500

@app.route('/api/call-single', methods=['POST'])
def call_single_number():
    """Make a call to a single number"""
    if not call_manager:
        return jsonify({
            "status": "error",
            "message": "CallManager not initialized. Check Twilio credentials."
        }), 500
    
    try:
        data = request.get_json()
        if not data or not data.get('number'):
            return jsonify({
                "status": "error",
                "message": "Phone number is required"
            }), 400
        
        phone_number = data.get('number', '').strip()
        custom_message = data.get('message')
        
        if not phone_number:
            return jsonify({
                "status": "error",
                "message": "Empty phone number provided"
            }), 400
        
        # Make the call
        result = call_manager.make_call(phone_number, custom_message)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error making single call: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error making call: {str(e)}"
        }), 500

@app.route('/api/call-status/<call_sid>')
def get_call_status(call_sid):
    """Get status of a specific call"""
    if not call_manager:
        return jsonify({
            "status": "error",
            "message": "CallManager not initialized"
        }), 500
    
    try:
        if not call_sid:
            return jsonify({
                "status": "error",
                "message": "Call SID is required"
            }), 400
        
        # Get call status
        result = call_manager.get_call_status(call_sid)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting call status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error getting call status: {str(e)}"
        }), 500

@app.route('/api/validate-number', methods=['POST'])
def validate_number():
    """Validate a phone number"""
    try:
        data = request.get_json()
        if not data or not data.get('number'):
            return jsonify({
                "status": "error",
                "message": "Phone number is required"
            }), 400
        
        phone_number = data.get('number', '').strip()
        
        if not phone_number:
            return jsonify({
                "status": "error",
                "message": "Empty phone number provided"
            }), 400
        
        # Validate using models function
        from models import validate_phone_number
        is_valid, result = validate_phone_number(phone_number)
        
        if is_valid:
            return jsonify({
                "status": "success",
                "valid": True,
                "formatted_number": result,
                "original_number": phone_number
            })
        else:
            return jsonify({
                "status": "success",
                "valid": False,
                "error": result,
                "original_number": phone_number
            })
        
    except Exception as e:
        logger.error(f"Error validating number: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error validating number: {str(e)}"
        }), 500

@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    """Handle file upload for phone numbers"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No file provided"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No file selected"
            }), 400
        
        # Check file type
        allowed_extensions = {'txt', 'csv'}
        if not ('.' in file.filename and 
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({
                "status": "error",
                "message": "File type not allowed. Please use .txt or .csv files."
            }), 400
        
        # Read file content
        try:
            file_content = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return jsonify({
                "status": "error",
                "message": "File encoding not supported. Please use UTF-8 encoded files."
            }), 400
        
        # Process the file content using command handler
        if not command_handler:
            return jsonify({
                "status": "error",
                "message": "Command Handler not initialized"
            }), 500
        
        result = command_handler.process_bulk_number_input(file_content)
        
        # Add file info to result
        result["file_info"] = {
            "filename": file.filename,
            "size": len(file_content)
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error processing file: {str(e)}"
        }), 500

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        dashboard_data = {
            "phone_numbers": {
                "count": 0,
                "recent": []
            },
            "call_statistics": {
                "total_calls": 0,
                "success_rate": 0,
                "recent_calls": []
            },
            "system_status": {
                "call_manager": "unknown",
                "command_handler": "unknown",
                "database": "unknown"
            }
        }
        
        # Get phone numbers data
        try:
            numbers = get_all_phone_numbers()
            dashboard_data["phone_numbers"]["count"] = len(numbers)
            dashboard_data["phone_numbers"]["recent"] = numbers[:5]  # Last 5 numbers
        except Exception as e:
            logger.warning(f"Error getting phone numbers for dashboard: {e}")
        
        # Get call statistics
        if call_manager:
            try:
                stats_result = call_manager.get_call_statistics_summary()
                if stats_result.get("status") == "success":
                    stats = stats_result.get("statistics", {})
                    dashboard_data["call_statistics"]["total_calls"] = stats.get("total_calls", 0)
                    dashboard_data["call_statistics"]["success_rate"] = stats.get("success_rate", 0)
                
                # Get recent call logs
                logs_result = call_manager.get_recent_call_logs(limit=5)
                if logs_result.get("status") == "success":
                    dashboard_data["call_statistics"]["recent_calls"] = logs_result.get("call_logs", [])
                    
            except Exception as e:
                logger.warning(f"Error getting call statistics for dashboard: {e}")
        
        # Get system status
        try:
            if call_manager:
                cm_test = call_manager.test_connection()
                dashboard_data["system_status"]["call_manager"] = cm_test.get("status", "failed")
            
            if command_handler:
                ch_test = command_handler.test_system()
                dashboard_data["system_status"]["command_handler"] = ch_test.get("test_results", {}).get("overall_status", "failed")
            
            # Test database
            get_phone_number_count()
            dashboard_data["system_status"]["database"] = "operational"
            
        except Exception as e:
            logger.warning(f"Error getting system status for dashboard: {e}")
            dashboard_data["system_status"]["database"] = "error"
        
        return jsonify({
            "status": "success",
            "data": dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error getting dashboard data: {str(e)}"
        }), 500

@app.route('/logs/status')
def get_logging_status():
    """Get logging system status and statistics"""
    try:
        if logging_manager:
            stats = logging_manager.get_log_stats()
            return jsonify({
                "status": "success",
                "logging_stats": stats
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Logging manager not initialized"
            }), 500
    except Exception as e:
        logger.error(f"Error getting logging status: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving logging status: {str(e)}"
        }), 500

@app.route('/logs/debug', methods=['POST'])
def toggle_debug_mode():
    """Toggle debug mode on/off"""
    try:
        data = request.get_json() or {}
        debug_enabled = data.get('debug', False)
        
        if logging_manager:
            logging_manager.set_debug_mode(debug_enabled)
            log_system_event("debug_mode_changed", enabled=debug_enabled)
            
            return jsonify({
                "status": "success",
                "message": f"Debug mode {'enabled' if debug_enabled else 'disabled'}",
                "debug_mode": debug_enabled
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Logging manager not initialized"
            }), 500
    except Exception as e:
        logger.error(f"Error toggling debug mode: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error toggling debug mode: {str(e)}"
        }), 500

@app.route('/remove-number', methods=['POST'])
@handle_errors(operation="remove_number")
def remove_number_endpoint():
    """Remove a phone number via POST"""
    try:
        data = request.get_json()
        if not data or not data.get('number'):
            raise ValidationError(
                message="Phone number is required",
                field="number"
            )
        
        number = data.get('number').strip()
        success, message = remove_phone_number(number)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message,
                "number": number
            })
        else:
            return jsonify({
                "status": "error", 
                "message": message,
                "number": number
            }), 400
            
    except Exception as e:
        logger.error(f"Error removing number: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error removing number: {str(e)}"
        }), 500

@app.route('/call-progress', methods=['GET'])
def get_call_progress():
    """Get current call progress"""
    # For now, return mock progress since we don't have active call tracking
    return jsonify({
        "status": "success",
        "progress": {
            "current_number": None,
            "current_index": 0,
            "total": 0,
            "completed": True,
            "estimated_time": "0s"
        }
    })

@app.route('/call-stats', methods=['GET'])
def get_call_stats():
    """Get call statistics"""
    if not call_manager:
        return jsonify({
            "status": "error",
            "message": "CallManager not initialized"
        }), 500
    
    try:
        result = call_manager.get_call_statistics_summary()
        return jsonify({
            "status": "success",
            "stats": result.get("statistics", {})
        })
    except Exception as e:
        logger.error(f"Error getting call stats: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error getting call stats: {str(e)}"
        }), 500

@app.route('/stop-calling', methods=['POST'])
def stop_calling():
    """Stop bulk calling"""
    return jsonify({
        "status": "success",
        "message": "Calling stopped (not implemented yet)"
    })

@app.route('/clear-logs', methods=['POST'])
def clear_logs():
    """Clear call logs"""
    try:
        from models import clear_call_logs
        success, message = clear_call_logs()
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            })
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 500
            
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error clearing logs: {str(e)}"
        }), 500

@app.route('/export-logs', methods=['GET'])
def export_logs():
    """Export call logs as CSV"""
    try:
        from models import get_call_logs
        import csv
        import io
        
        logs = get_call_logs(limit=1000)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Phone Number', 'Call SID', 'Status', 'Duration', 'Error Message', 'Created At'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.get('phone_number', ''),
                log.get('call_sid', ''),
                log.get('status', ''),
                log.get('duration', 0),
                log.get('error_message', ''),
                log.get('created_at', '')
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=call_logs.csv'}
        )
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error exporting logs: {str(e)}"
        }), 500

@app.route('/start-calling', methods=['POST'])
@handle_errors(operation="start_calling")
def start_calling():
    """Initiate bulk calling with comprehensive logging"""
    if not call_manager:
        error_msg = call_manager_error or "CallManager not initialized"
        raise ConfigurationError(
            message=f"CallManager unavailable: {error_msg}",
            config_key="call_manager"
        )
    
    try:
        # Get phone numbers from database
        with LoggedOperation("get_phone_numbers_for_calling"):
            phone_numbers_data = get_all_phone_numbers()
            phone_numbers = [item['number'] for item in phone_numbers_data]
        
        if not phone_numbers:
            raise ValidationError(
                message="No phone numbers found. Please add numbers first.",
                field="phone_numbers",
                value=len(phone_numbers)
            )
        
        # Get and validate request data
        data = request.get_json() or {}
        custom_message = data.get('message')
        delay_between_calls = data.get('delay', 2)
        
        # Validate delay
        if not isinstance(delay_between_calls, (int, float)) or delay_between_calls < 0:
            raise ValidationError(
                message="Delay must be a non-negative number",
                field="delay",
                value=delay_between_calls
            )
        
        # Log the bulk calling initiation
        log_user_action("start_bulk_calling", 
                       user_input=f"{len(phone_numbers)} numbers, delay={delay_between_calls}s")
        
        logger.info(f"Starting bulk calling for {len(phone_numbers)} numbers")
        
        # Start bulk calling
        with LoggedOperation("bulk_calling", 
                           phone_count=len(phone_numbers), 
                           delay=delay_between_calls):
            result = call_manager.bulk_call(
                phone_numbers=phone_numbers,
                message=custom_message,
                delay_between_calls=delay_between_calls
            )
        
        # Log the result
        log_user_action("bulk_calling_completed", result=result)
        log_system_event("bulk_calling_finished", 
                        phone_count=len(phone_numbers),
                        success_count=result.get('statistics', {}).get('successful', 0),
                        failed_count=result.get('statistics', {}).get('failed', 0))
        
        return jsonify(result)
        
    except (ValidationError, ConfigurationError):
        raise  # Re-raise our custom errors
    except Exception as e:
        log_error_with_context(e, "start_calling", phone_count=len(phone_numbers) if 'phone_numbers' in locals() else 0)
        raise

if __name__ == '__main__':
    app.run(debug=True)