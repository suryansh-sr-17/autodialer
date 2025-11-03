import logging
from typing import Dict, Any, List, Optional
from ai_processor import AIProcessor
from call_manager import CallManager
from models import (
    add_phone_number, 
    remove_phone_number, 
    get_all_phone_numbers,
    phone_number_exists,
    add_multiple_phone_numbers
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandExecutionHandler:
    """
    Handles execution of AI-parsed commands with integrated responses
    """
    
    def __init__(self, gemini_api_key=None):
        """Initialize command handler with AI processor and call manager"""
        try:
            self.ai_processor = AIProcessor(gemini_api_key=gemini_api_key)
            logger.info("AI Processor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Processor: {e}")
            self.ai_processor = None
        
        try:
            self.call_manager = CallManager()
            logger.info("Call Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Call Manager: {e}")
            self.call_manager = None
    
    def process_and_execute_command(self, user_input: str) -> Dict[str, Any]:
        """
        Process natural language command and execute the corresponding action
        
        Args:
            user_input (str): User's natural language command
        
        Returns:
            dict: Complete result with parsed command, execution result, and AI response
        """
        if not self.ai_processor:
            return {
                "status": "error",
                "error": "AI Processor not available",
                "response": "Sorry, I'm having trouble understanding commands right now. Please try again later."
            }
        
        logger.info(f"Processing command: {user_input}")
        
        # Parse the command using AI
        parsed_command = self.ai_processor.process_command(user_input)
        
        # Validate command parameters
        action = parsed_command.get("action", "unknown")
        parameters = parsed_command.get("parameters", {})
        
        is_valid, validation_error = self.ai_processor.validate_command_parameters(action, parameters)
        
        if not is_valid:
            return {
                "status": "error",
                "parsed_command": parsed_command,
                "error": validation_error,
                "response": self._generate_error_response(validation_error, user_input)
            }
        
        # Execute the command
        execution_result = self._execute_command(action, parameters)
        
        # Generate AI response
        ai_response = self._generate_ai_response(execution_result, user_input, parsed_command)
        
        # Combine all results
        complete_result = {
            "status": execution_result.get("status", "unknown"),
            "parsed_command": parsed_command,
            "execution_result": execution_result,
            "response": ai_response,
            "timestamp": parsed_command.get("timestamp")
        }
        
        logger.info(f"Command processing completed: {action} -> {execution_result.get('status', 'unknown')}")
        
        return complete_result
    
    def _execute_command(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the parsed command based on action type
        
        Args:
            action (str): Command action to execute
            parameters (dict): Command parameters
        
        Returns:
            dict: Execution result
        """
        try:
            if action == "call_all":
                return self._handle_call_all(parameters)
            
            elif action == "call_specific":
                return self._handle_call_specific(parameters)
            
            elif action == "add_number":
                return self._handle_add_number(parameters)
            
            elif action == "remove_number":
                return self._handle_remove_number(parameters)
            
            elif action == "view_logs":
                return self._handle_view_logs(parameters)
            
            elif action == "get_statistics":
                return self._handle_get_statistics(parameters)
            
            else:
                return {
                    "status": "error",
                    "action": action,
                    "error": f"Unknown action: {action}",
                    "suggestion": "Try commands like 'call all numbers', 'add +919876543210', or 'show call logs'"
                }
        
        except Exception as e:
            logger.error(f"Error executing command {action}: {e}")
            return {
                "status": "error",
                "action": action,
                "error": f"Execution failed: {str(e)}",
                "parameters": parameters
            }
    
    def _handle_call_all(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'call all numbers' command"""
        if not self.call_manager:
            return {
                "status": "error",
                "action": "call_all",
                "error": "Call Manager not available. Check Twilio configuration."
            }
        
        # Get all phone numbers from database
        phone_numbers_data = get_all_phone_numbers()
        phone_numbers = [item['number'] for item in phone_numbers_data]
        
        if not phone_numbers:
            return {
                "status": "error",
                "action": "call_all",
                "error": "No phone numbers found in database. Please add numbers first.",
                "suggestion": "Try adding numbers with commands like 'add +919876543210'"
            }
        
        # Get custom message if provided
        custom_message = parameters.get("message")
        delay = parameters.get("delay", 2)
        
        # Start bulk calling
        result = self.call_manager.bulk_call(
            phone_numbers=phone_numbers,
            message=custom_message,
            delay_between_calls=delay
        )
        
        if result.get("status") == "completed":
            return {
                "status": "success",
                "action": "call_all",
                "statistics": result.get("statistics", {}),
                "total_numbers": len(phone_numbers),
                "message": custom_message,
                "results": result.get("results", [])
            }
        else:
            return {
                "status": "error",
                "action": "call_all",
                "error": result.get("error", "Bulk calling failed"),
                "statistics": result.get("statistics", {})
            }
    
    def _handle_call_specific(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'call specific number' command"""
        if not self.call_manager:
            return {
                "status": "error",
                "action": "call_specific",
                "error": "Call Manager not available. Check Twilio configuration."
            }
        
        phone_number = parameters.get("phone_number")
        custom_message = parameters.get("message")
        
        # Make the call
        result = self.call_manager.make_call(phone_number, custom_message)
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "action": "call_specific",
                "phone_number": phone_number,
                "call_sid": result.get("call_sid"),
                "message": custom_message
            }
        else:
            return {
                "status": "error",
                "action": "call_specific",
                "phone_number": phone_number,
                "error": result.get("error", "Call failed")
            }
    
    def _handle_add_number(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'add number' command"""
        phone_number = parameters.get("phone_number")
        
        # Check if number already exists
        if phone_number_exists(phone_number):
            return {
                "status": "error",
                "action": "add_number",
                "phone_number": phone_number,
                "error": "Phone number already exists in the database"
            }
        
        # Add the number
        add_result = add_phone_number(phone_number)
        
        if add_result.get('status') == 'success':
            return {
                "status": "success",
                "action": "add_number",
                "phone_number": phone_number,
                "message": add_result.get('message', 'Number added successfully')
            }
        else:
            return {
                "status": "error",
                "action": "add_number",
                "phone_number": phone_number,
                "error": add_result.get('message', 'Failed to add number')
            }
    
    def _handle_remove_number(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'remove number' command"""
        phone_number = parameters.get("phone_number")
        
        # Remove the number
        success, message = remove_phone_number(phone_number)
        
        if success:
            return {
                "status": "success",
                "action": "remove_number",
                "phone_number": phone_number,
                "message": message
            }
        else:
            return {
                "status": "error",
                "action": "remove_number",
                "phone_number": phone_number,
                "error": message
            }
    
    def _handle_view_logs(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'view call logs' command"""
        if not self.call_manager:
            return {
                "status": "error",
                "action": "view_logs",
                "error": "Call Manager not available"
            }
        
        # Get parameters for filtering
        limit = parameters.get("limit", 50)
        phone_number = parameters.get("phone_number")
        status_filter = parameters.get("status")
        
        # Get call logs
        result = self.call_manager.get_recent_call_logs(
            limit=limit,
            phone_number=phone_number,
            status=status_filter
        )
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "action": "view_logs",
                "call_logs": result.get("call_logs", []),
                "count": result.get("count", 0),
                "filters": {
                    "limit": limit,
                    "phone_number": phone_number,
                    "status": status_filter
                }
            }
        else:
            return {
                "status": "error",
                "action": "view_logs",
                "error": result.get("error", "Failed to retrieve call logs")
            }
    
    def _handle_get_statistics(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle 'get statistics' command"""
        if not self.call_manager:
            return {
                "status": "error",
                "action": "get_statistics",
                "error": "Call Manager not available"
            }
        
        # Get parameters for filtering
        phone_number = parameters.get("phone_number")
        days = parameters.get("days")
        
        # Get statistics
        result = self.call_manager.get_call_statistics_summary(
            phone_number=phone_number,
            days=days
        )
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "action": "get_statistics",
                "statistics": result.get("statistics", {}),
                "filters": {
                    "phone_number": phone_number,
                    "days": days
                }
            }
        else:
            return {
                "status": "error",
                "action": "get_statistics",
                "error": result.get("error", "Failed to retrieve statistics")
            }
    
    def _generate_ai_response(self, execution_result: Dict[str, Any], original_command: str, parsed_command: Dict[str, Any]) -> str:
        """
        Generate AI response for the execution result
        
        Args:
            execution_result (dict): Result from command execution
            original_command (str): Original user command
            parsed_command (dict): Parsed command details
        
        Returns:
            str: AI-generated response
        """
        if self.ai_processor:
            try:
                return self.ai_processor.generate_response(execution_result, original_command)
            except Exception as e:
                logger.warning(f"AI response generation failed: {e}")
        
        # Fallback to simple response
        return self._generate_simple_response(execution_result, original_command)
    
    def _generate_error_response(self, error_message: str, original_command: str) -> str:
        """Generate response for validation errors"""
        if "phone number" in error_message.lower():
            return f"❌ {error_message}. Please provide a valid Indian phone number (e.g., +919876543210 or 1800123456)."
        elif "not recognized" in error_message.lower():
            return f"🤔 I didn't understand that command. Try something like:\n• 'Call all numbers'\n• 'Add +919876543210'\n• 'Show call logs'\n• 'Remove +919876543210'"
        else:
            return f"❌ {error_message}"
    
    def _generate_simple_response(self, execution_result: Dict[str, Any], original_command: str) -> str:
        """Generate simple response when AI is not available"""
        status = execution_result.get("status", "unknown")
        action = execution_result.get("action", "unknown")
        
        if status == "success":
            if action == "call_all":
                stats = execution_result.get("statistics", {})
                total = stats.get("total", 0)
                successful = stats.get("successful", 0)
                return f"✅ Started calling {total} numbers! {successful} calls initiated successfully."
            
            elif action == "call_specific":
                phone_number = execution_result.get("phone_number", "the number")
                return f"✅ Calling {phone_number} now! Check the call logs for status updates."
            
            elif action == "add_number":
                phone_number = execution_result.get("phone_number", "the number")
                return f"✅ Successfully added {phone_number} to your contact list!"
            
            elif action == "remove_number":
                phone_number = execution_result.get("phone_number", "the number")
                return f"✅ Successfully removed {phone_number} from your contact list!"
            
            elif action == "view_logs":
                count = execution_result.get("count", 0)
                return f"📋 Retrieved {count} call log entries. Check the display above for details!"
            
            elif action == "get_statistics":
                stats = execution_result.get("statistics", {})
                total = stats.get("total_calls", 0)
                success_rate = stats.get("success_rate", 0)
                return f"📊 Call Statistics: {total} total calls with {success_rate}% success rate!"
        
        elif status == "error":
            error_msg = execution_result.get("error", "Unknown error occurred")
            suggestion = execution_result.get("suggestion", "")
            
            response = f"❌ {error_msg}"
            if suggestion:
                response += f"\n💡 {suggestion}"
            
            return response
        
        return "🤔 Command processed, but I'm not sure about the result. Please check the interface for updates."
    
    def process_bulk_number_input(self, text_input: str) -> Dict[str, Any]:
        """
        Process bulk number input from text (for copy-paste functionality)
        
        Args:
            text_input (str): Text containing multiple phone numbers
        
        Returns:
            dict: Processing result with added numbers and errors
        """
        if not self.ai_processor:
            return {
                "status": "error",
                "error": "AI Processor not available",
                "response": "Sorry, I can't process bulk numbers right now."
            }
        
        # Extract phone numbers from text
        valid_numbers, invalid_numbers = self.ai_processor.extract_phone_numbers_from_text(text_input)
        
        if not valid_numbers and not invalid_numbers:
            return {
                "status": "error",
                "error": "No phone numbers found in the input text",
                "response": "I couldn't find any phone numbers in that text. Please make sure to include valid Indian phone numbers."
            }
        
        # Add valid numbers to database
        result = {"status": "success", "valid_numbers": [], "invalid_numbers": invalid_numbers, "errors": []}
        
        if valid_numbers:
            add_result = add_multiple_phone_numbers(valid_numbers)
            
            result["valid_numbers"] = add_result.get("added", [])
            result["duplicates"] = add_result.get("duplicates", [])
            result["errors"].extend(add_result.get("errors", []))
            result["invalid_numbers"].extend([item["number"] for item in add_result.get("invalid", [])])
        
        # Generate response
        total_added = len(result["valid_numbers"])
        total_duplicates = len(result.get("duplicates", []))
        total_invalid = len(result["invalid_numbers"])
        
        if total_added > 0:
            response = f"✅ Successfully added {total_added} phone numbers!"
            if total_duplicates > 0:
                response += f" ({total_duplicates} were already in your list)"
            if total_invalid > 0:
                response += f"\n⚠️ {total_invalid} numbers were invalid and skipped."
        elif total_duplicates > 0:
            response = f"ℹ️ All {total_duplicates} numbers were already in your list."
        else:
            response = f"❌ No valid numbers could be added. {total_invalid} numbers were invalid."
        
        result["response"] = response
        return result
    
    def test_system(self) -> Dict[str, Any]:
        """
        Test all system components
        
        Returns:
            dict: System test results
        """
        results = {
            "ai_processor": "not_available",
            "call_manager": "not_available",
            "overall_status": "unknown"
        }
        
        # Test AI Processor
        if self.ai_processor:
            ai_test = self.ai_processor.test_connection()
            results["ai_processor"] = ai_test.get("status", "failed")
            results["ai_details"] = ai_test
        
        # Test Call Manager
        if self.call_manager:
            call_test = self.call_manager.test_connection()
            results["call_manager"] = call_test.get("status", "failed")
            results["call_details"] = call_test
        
        # Determine overall status
        if results["ai_processor"] == "success" and results["call_manager"] == "success":
            results["overall_status"] = "fully_operational"
        elif results["ai_processor"] == "success" or results["call_manager"] == "success":
            results["overall_status"] = "partially_operational"
        else:
            results["overall_status"] = "not_operational"
        
        return {
            "status": "success",
            "test_results": results,
            "message": f"System is {results['overall_status'].replace('_', ' ')}"
        }