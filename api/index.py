"""
Vercel-compatible serverless entry point for Autodialer Application
"""

import os
import sys
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure basic logging for serverless environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
           template_folder='../templates',
           static_folder='../static')

# Basic configuration for serverless
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = False

# Enable CORS
CORS(app)

# Import configuration and models with error handling
try:
    from config import Config
    app.config.from_object(Config)
except Exception as e:
    logger.warning(f"Could not load config: {e}")

# Global variables for components
call_manager = None
command_handler = None
db_initialized = False

def initialize_components():
    """Initialize components lazily when first needed"""
    global call_manager, command_handler, db_initialized
    
    if not db_initialized:
        try:
            from models import init_db
            init_db()
            db_initialized = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    if call_manager is None:
        try:
            from call_manager import CallManager
            call_manager = CallManager()
            logger.info("CallManager initialized successfully")
        except Exception as e:
            logger.error(f"CallManager initialization failed: {e}")
    
    if command_handler is None:
        try:
            from command_handlers import CommandExecutionHandler
            command_handler = CommandExecutionHandler()
            logger.info("CommandHandler initialized successfully")
        except Exception as e:
            logger.error(f"CommandHandler initialization failed: {e}")

@app.route('/')
def index():
    """Main interface page"""
    try:
        initialize_components()
        
        # Get basic system info
        try:
            from models import get_phone_number_count
            phone_count = get_phone_number_count()
        except:
            phone_count = 0
        
        system_info = {
            "call_manager_available": call_manager is not None,
            "command_handler_available": command_handler is not None,
            "phone_count": phone_count
        }
        
        return render_template('index.html', system_info=system_info)
        
    except Exception as e:
        logger.error(f"Error loading main page: {e}")
        return render_template('index.html', system_info={
            "call_manager_available": False,
            "command_handler_available": False,
            "phone_count": 0
        })

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        initialize_components()
        
        health_status = {
            "status": "healthy",
            "components": {
                "database": "unknown",
                "call_manager": "not_initialized",
                "command_handler": "not_initialized"
            }
        }
        
        # Check database
        try:
            from models import get_phone_number_count
            count = get_phone_number_count()
            health_status["components"]["database"] = "operational"
        except Exception as e:
            health_status["components"]["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Call Manager
        if call_manager:
            health_status["components"]["call_manager"] = "operational"
        else:
            health_status["components"]["call_manager"] = "failed"
            health_status["status"] = "degraded"
        
        # Check Command Handler
        if command_handler:
            health_status["components"]["command_handler"] = "operational"
        else:
            health_status["components"]["command_handler"] = "failed"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

@app.route('/numbers', methods=['GET'])
@app.route('/get-numbers', methods=['GET'])
def get_numbers():
    """Get all phone numbers"""
    try:
        initialize_components()
        from models import get_all_phone_numbers, get_phone_number_count
        
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
        initialize_components()
        
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
        
        from models import add_phone_number
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

@app.route('/upload-numbers', methods=['POST'])
def upload_numbers():
    """Handle number uploads/paste"""
    try:
        initialize_components()
        
        if not command_handler:
            return jsonify({
                "status": "error",
                "message": "Command Handler not initialized. Check API credentials."
            }), 500
        
        data = request.get_json()
        if not data or not data.get('numbers'):
            return jsonify({
                "status": "error",
                "message": "Numbers are required"
            }), 400
        
        numbers_input = data.get('numbers')
        
        # Convert list to string if needed
        if isinstance(numbers_input, list):
            numbers_text = '\n'.join(str(num) for num in numbers_input)
        else:
            numbers_text = str(numbers_input).strip()
        
        if not numbers_text:
            return jsonify({
                "status": "error",
                "message": "Numbers input cannot be empty"
            }), 400
        
        # Process bulk number input
        result = command_handler.process_bulk_number_input(numbers_text)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in bulk number processing: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to process numbers: {str(e)}"
        }), 500

@app.route('/ai-command', methods=['POST'])
def ai_command():
    """Process AI prompt commands"""
    try:
        initialize_components()
        
        if not command_handler:
            return jsonify({
                "status": "error",
                "message": "AI Command Handler not initialized. Check API credentials."
            }), 500
        
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
        logger.error(f"Error processing AI command: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error processing AI command: {str(e)}"
        }), 500

@app.route('/start-calling', methods=['POST'])
def start_calling():
    """Initiate bulk calling"""
    try:
        initialize_components()
        
        if not call_manager:
            return jsonify({
                "status": "error",
                "message": "CallManager not initialized. Check Twilio credentials."
            }), 500
        
        # Get phone numbers from database
        from models import get_all_phone_numbers
        phone_numbers_data = get_all_phone_numbers()
        phone_numbers = [item['number'] for item in phone_numbers_data]
        
        if not phone_numbers:
            return jsonify({
                "status": "error",
                "message": "No phone numbers found. Please add numbers first."
            }), 400
        
        # Get request data
        data = request.get_json() or {}
        custom_message = data.get('message')
        delay_between_calls = data.get('delay', 2)
        
        logger.info(f"Starting bulk calling for {len(phone_numbers)} numbers")
        
        # Start bulk calling
        result = call_manager.bulk_call(
            phone_numbers=phone_numbers,
            message=custom_message,
            delay_between_calls=delay_between_calls
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error starting bulk calling: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error starting bulk calling: {str(e)}"
        }), 500

@app.route('/call-logs')
def call_logs():
    """Retrieve call history"""
    try:
        initialize_components()
        
        if not call_manager:
            return jsonify({
                "status": "error",
                "message": "CallManager not initialized"
            }), 500
        
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
        logger.error(f"Error retrieving call logs: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving call logs: {str(e)}"
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "error_code": "NOT_FOUND"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "error_code": "INTERNAL_ERROR"
    }), 500

# Vercel requires the app to be available as 'app'
# This is the entry point for Vercel
if __name__ == '__main__':
    app.run(debug=False)