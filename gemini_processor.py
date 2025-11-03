import os
import re
import json
import logging
import google.generativeai as genai
from typing import Dict, List, Optional, Any
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiProcessor:
    """Handles Gemini API integration for natural language processing"""
    
    def __init__(self, api_key=None):
        """Initialize Gemini API client with API key from environment variables"""
        self.api_key = api_key or Config.GEMINI_API_KEY
        
        if not self.api_key:
            raise ValueError("Gemini API key is required. Please set GEMINI_API_KEY environment variable.")
        
        # Configure Gemini API
        try:
            genai.configure(api_key=self.api_key)
            
            # Initialize the model (using the latest stable model)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            
            logger.info("Gemini API client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API client: {e}")
            raise
        
        # Define command patterns and examples for prompt engineering
        self.command_patterns = {
            "call_all": [
                "call all numbers",
                "start calling everyone",
                "dial all contacts",
                "begin bulk calling",
                "call everyone in the list"
            ],
            "call_specific": [
                "call +919876543210",
                "dial 1800123456",
                "phone +911234567890",
                "call this number: +919876543210"
            ],
            "add_number": [
                "add +919876543210",
                "add number +911234567890",
                "save this number: +919876543210",
                "include +911800123456 in the list"
            ],
            "remove_number": [
                "remove +919876543210",
                "delete number +911234567890",
                "remove this number: +919876543210",
                "delete +911800123456 from the list"
            ],
            "view_logs": [
                "show call logs",
                "view call history",
                "display recent calls",
                "show me the call statistics",
                "what calls were made today"
            ],
            "get_statistics": [
                "show statistics",
                "call stats",
                "how many calls were successful",
                "show me the success rate",
                "display call analytics"
            ]
        }
    
    def create_command_parsing_prompt(self, user_input: str) -> str:
        """
        Create a structured prompt for Gemini to parse user commands
        
        Args:
            user_input (str): User's natural language input
        
        Returns:
            str: Formatted prompt for Gemini API
        """
        prompt = f"""
You are an AI assistant for an autodialer application. Parse the following user command and extract the action and parameters.

User Input: "{user_input}"

Available Actions:
1. call_all - Start calling all numbers in the database
2. call_specific - Call a specific phone number
3. add_number - Add a phone number to the database
4. remove_number - Remove a phone number from the database
5. view_logs - Show call logs and history
6. get_statistics - Display call statistics and analytics

Response Format (JSON only):
{{
    "action": "action_name",
    "parameters": {{
        "phone_number": "extracted_phone_number_if_any",
        "message": "custom_message_if_specified",
        "additional_params": "any_other_relevant_parameters"
    }},
    "confidence": 0.95,
    "explanation": "Brief explanation of the parsed command"
}}

Examples:
- "Call all numbers" → {{"action": "call_all", "parameters": {{}}, "confidence": 0.98}}
- "Add +919876543210" → {{"action": "add_number", "parameters": {{"phone_number": "+919876543210"}}, "confidence": 0.95}}
- "Call +911800123456 with message hello" → {{"action": "call_specific", "parameters": {{"phone_number": "+911800123456", "message": "hello"}}, "confidence": 0.92}}

Important:
- Extract phone numbers in international format (+91 for India)
- If no clear action is identified, use "unknown" as action
- Confidence should be between 0.0 and 1.0
- Only respond with valid JSON, no additional text

Parse the user input now:
"""
        return prompt
    
    def parse_command(self, user_input: str) -> Dict[str, Any]:
        """
        Parse natural language command using Gemini API
        
        Args:
            user_input (str): User's natural language input
        
        Returns:
            dict: Parsed command with action, parameters, and confidence
        """
        if not user_input or not user_input.strip():
            return {
                "action": "unknown",
                "parameters": {},
                "confidence": 0.0,
                "explanation": "Empty input provided",
                "error": "No input provided"
            }
        
        try:
            logger.info(f"Parsing command: {user_input}")
            
            # Create the prompt
            prompt = self.create_command_parsing_prompt(user_input.strip())
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini API")
                return self._fallback_parsing(user_input)
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response.text.strip())
                
                # Validate response structure
                if not isinstance(parsed_response, dict):
                    raise ValueError("Response is not a dictionary")
                
                # Ensure required fields exist
                parsed_response.setdefault("action", "unknown")
                parsed_response.setdefault("parameters", {})
                parsed_response.setdefault("confidence", 0.5)
                parsed_response.setdefault("explanation", "Parsed by Gemini API")
                
                # Validate phone numbers if present
                if "phone_number" in parsed_response["parameters"]:
                    phone_number = parsed_response["parameters"]["phone_number"]
                    validated_number = self._validate_and_format_phone_number(phone_number)
                    if validated_number:
                        parsed_response["parameters"]["phone_number"] = validated_number
                    else:
                        parsed_response["parameters"]["phone_number_error"] = f"Invalid phone number: {phone_number}"
                
                logger.info(f"Successfully parsed command: {parsed_response['action']}")
                return parsed_response
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response from Gemini: {e}")
                logger.debug(f"Raw response: {response.text}")
                return self._fallback_parsing(user_input)
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return self._fallback_parsing(user_input)
    
    def _fallback_parsing(self, user_input: str) -> Dict[str, Any]:
        """
        Fallback regex-based parsing when Gemini API fails
        
        Args:
            user_input (str): User's input to parse
        
        Returns:
            dict: Parsed command using regex patterns
        """
        logger.info("Using fallback regex parsing")
        
        user_input_lower = user_input.lower().strip()
        
        # Phone number extraction regex
        phone_pattern = r'(\+91|91)?[\s-]?([6-9]\d{9}|1800\d{7})'
        phone_matches = re.findall(phone_pattern, user_input)
        
        extracted_phone = None
        if phone_matches:
            # Format the phone number
            prefix, number = phone_matches[0]
            if prefix:
                extracted_phone = f"+91{number}"
            else:
                extracted_phone = f"+91{number}"
        
        # Action detection using keywords
        if any(keyword in user_input_lower for keyword in ["call all", "dial all", "start calling", "bulk call"]):
            return {
                "action": "call_all",
                "parameters": {},
                "confidence": 0.8,
                "explanation": "Detected bulk calling command (fallback parsing)"
            }
        
        elif extracted_phone and any(keyword in user_input_lower for keyword in ["call", "dial", "phone"]):
            return {
                "action": "call_specific",
                "parameters": {"phone_number": extracted_phone},
                "confidence": 0.75,
                "explanation": "Detected specific number calling command (fallback parsing)"
            }
        
        elif extracted_phone and any(keyword in user_input_lower for keyword in ["add", "save", "include"]):
            return {
                "action": "add_number",
                "parameters": {"phone_number": extracted_phone},
                "confidence": 0.75,
                "explanation": "Detected add number command (fallback parsing)"
            }
        
        elif extracted_phone and any(keyword in user_input_lower for keyword in ["remove", "delete", "exclude"]):
            return {
                "action": "remove_number",
                "parameters": {"phone_number": extracted_phone},
                "confidence": 0.75,
                "explanation": "Detected remove number command (fallback parsing)"
            }
        
        elif any(keyword in user_input_lower for keyword in ["logs", "history", "calls made", "recent calls"]):
            return {
                "action": "view_logs",
                "parameters": {},
                "confidence": 0.7,
                "explanation": "Detected view logs command (fallback parsing)"
            }
        
        elif any(keyword in user_input_lower for keyword in ["statistics", "stats", "success rate", "analytics"]):
            return {
                "action": "get_statistics",
                "parameters": {},
                "confidence": 0.7,
                "explanation": "Detected statistics command (fallback parsing)"
            }
        
        else:
            return {
                "action": "unknown",
                "parameters": {},
                "confidence": 0.1,
                "explanation": "Could not parse command (fallback parsing)",
                "error": "Command not recognized"
            }
    
    def _validate_and_format_phone_number(self, phone_number: str) -> Optional[str]:
        """
        Validate and format phone number
        
        Args:
            phone_number (str): Phone number to validate
        
        Returns:
            str or None: Formatted phone number or None if invalid
        """
        if not phone_number:
            return None
        
        # Clean the number
        cleaned = re.sub(r'[^\d+]', '', phone_number.strip())
        
        # Indian phone number patterns
        patterns = [
            r'^(\+91|91)?([6-9]\d{9})$',  # Mobile numbers
            r'^(\+91|91)?(1800\d{7})$',   # Toll-free numbers
            r'^(\+91|91)?(\d{2,4}\d{6,8})$'  # Landline numbers
        ]
        
        for pattern in patterns:
            match = re.match(pattern, cleaned)
            if match:
                prefix, number = match.groups()
                return f"+91{number}"
        
        return None
    
    def generate_response(self, action_result: Dict[str, Any], original_command: str) -> str:
        """
        Generate natural language response using Gemini API
        
        Args:
            action_result (dict): Result from executing the parsed command
            original_command (str): Original user command
        
        Returns:
            str: Natural language response
        """
        try:
            # Create prompt for response generation
            prompt = f"""
Generate a natural, conversational response for an autodialer application user.

Original Command: "{original_command}"
Action Result: {json.dumps(action_result, indent=2)}

Guidelines:
- Be conversational and friendly
- Provide clear status updates
- Include relevant numbers/statistics when available
- Keep responses concise but informative
- If there's an error, explain it clearly and suggest next steps
- Use natural language, avoid technical jargon

Examples:
- For successful bulk calling: "Started calling 25 numbers. I'll update you on the progress!"
- For adding a number: "Added +919876543210 to your contact list successfully."
- For statistics: "You've made 50 calls today with a 78% success rate. Great job!"
- For errors: "I couldn't add that number because it's already in your list."

Generate a response now:
"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                generated_response = response.text.strip()
                logger.info("Generated natural language response using Gemini")
                return generated_response
            else:
                logger.warning("Empty response from Gemini for response generation")
                return self._fallback_response(action_result, original_command)
        
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            return self._fallback_response(action_result, original_command)
    
    def _fallback_response(self, action_result: Dict[str, Any], original_command: str) -> str:
        """
        Generate fallback response when Gemini API fails
        
        Args:
            action_result (dict): Result from executing the command
            original_command (str): Original user command
        
        Returns:
            str: Fallback response
        """
        status = action_result.get("status", "unknown")
        
        if status == "success":
            action = action_result.get("action", "unknown")
            
            if action == "call_all":
                stats = action_result.get("statistics", {})
                total = stats.get("total", 0)
                return f"Started calling {total} numbers. Check the call logs for progress updates."
            
            elif action == "call_specific":
                phone_number = action_result.get("phone_number", "the number")
                return f"Successfully initiated call to {phone_number}."
            
            elif action == "add_number":
                phone_number = action_result.get("phone_number", "the number")
                return f"Added {phone_number} to your contact list."
            
            elif action == "remove_number":
                phone_number = action_result.get("phone_number", "the number")
                return f"Removed {phone_number} from your contact list."
            
            elif action == "view_logs":
                count = action_result.get("count", 0)
                return f"Retrieved {count} call log entries. Check the display above for details."
            
            elif action == "get_statistics":
                stats = action_result.get("statistics", {})
                total = stats.get("total_calls", 0)
                success_rate = stats.get("success_rate", 0)
                return f"Call Statistics: {total} total calls with {success_rate}% success rate."
            
            else:
                return "Command executed successfully."
        
        elif status == "error" or status == "failed":
            error_msg = action_result.get("error", "Unknown error occurred")
            return f"Sorry, I couldn't complete that request: {error_msg}"
        
        else:
            return "I processed your request, but I'm not sure about the result. Please check the interface for updates."
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Gemini API connection
        
        Returns:
            dict: Connection test result
        """
        try:
            test_prompt = "Respond with 'Connection successful' if you can read this."
            response = self.model.generate_content(test_prompt)
            
            if response and response.text:
                logger.info("Gemini API connection test successful")
                return {
                    "status": "success",
                    "message": "Gemini API connection successful",
                    "response": response.text.strip()
                }
            else:
                return {
                    "status": "failed",
                    "message": "Empty response from Gemini API",
                    "response": None
                }
        
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return {
                "status": "failed",
                "message": f"Connection test failed: {str(e)}",
                "response": None
            }