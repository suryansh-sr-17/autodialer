import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from gemini_processor import GeminiProcessor
from models import validate_phone_number

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProcessor:
    """
    Advanced AI-powered command processor that combines Gemini API with structured parsing
    """
    
    def __init__(self, gemini_api_key=None):
        """Initialize AIProcessor with Gemini integration"""
        try:
            self.gemini_processor = GeminiProcessor(api_key=gemini_api_key)
            logger.info("AIProcessor initialized with Gemini integration")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini processor: {e}")
            self.gemini_processor = None
        
        # Enhanced command patterns for better recognition
        self.command_patterns = {
            "call_all": {
                "keywords": ["call all", "dial all", "start calling", "bulk call", "call everyone", "dial everyone"],
                "regex": r"(call|dial|start calling|phone)\s+(all|everyone|everybody|all numbers)",
                "confidence_boost": 0.1
            },
            "call_specific": {
                "keywords": ["call", "dial", "phone"],
                "regex": r"(call|dial|phone)\s*(\+?91?[\s-]?[6-9]\d{9}|\+?91?[\s-]?1800\d{7})",
                "confidence_boost": 0.15
            },
            "add_number": {
                "keywords": ["add", "save", "include", "insert"],
                "regex": r"(add|save|include|insert)\s*(number)?\s*(\+?91?[\s-]?[6-9]\d{9}|\+?91?[\s-]?1800\d{7})",
                "confidence_boost": 0.1
            },
            "remove_number": {
                "keywords": ["remove", "delete", "exclude", "drop"],
                "regex": r"(remove|delete|exclude|drop)\s*(number)?\s*(\+?91?[\s-]?[6-9]\d{9}|\+?91?[\s-]?1800\d{7})",
                "confidence_boost": 0.1
            },
            "view_logs": {
                "keywords": ["logs", "history", "calls made", "recent calls", "call log", "show calls"],
                "regex": r"(show|view|display|get)\s*(call)?\s*(logs?|history|recent calls)",
                "confidence_boost": 0.05
            },
            "get_statistics": {
                "keywords": ["statistics", "stats", "success rate", "analytics", "performance", "summary"],
                "regex": r"(show|get|display)\s*(call)?\s*(statistics|stats|success rate|analytics|performance|summary)",
                "confidence_boost": 0.05
            }
        }
    
    def process_command(self, user_input: str) -> Dict[str, Any]:
        """
        Process natural language command with enhanced parsing
        
        Args:
            user_input (str): User's natural language input
        
        Returns:
            dict: Processed command with action, parameters, and metadata
        """
        if not user_input or not user_input.strip():
            return {
                "action": "unknown",
                "parameters": {},
                "confidence": 0.0,
                "explanation": "Empty input provided",
                "error": "No input provided",
                "processing_method": "validation"
            }
        
        logger.info(f"Processing command: {user_input}")
        
        # First, try Gemini API if available
        gemini_result = None
        if self.gemini_processor:
            try:
                gemini_result = self.gemini_processor.parse_command(user_input)
                logger.info(f"Gemini parsing result: {gemini_result.get('action', 'unknown')}")
            except Exception as e:
                logger.warning(f"Gemini processing failed: {e}")
        
        # Always run structured parsing for comparison/fallback
        structured_result = self._structured_parsing(user_input)
        logger.info(f"Structured parsing result: {structured_result.get('action', 'unknown')}")
        
        # Combine results intelligently
        final_result = self._combine_parsing_results(gemini_result, structured_result, user_input)
        
        # Extract and validate phone numbers
        final_result = self._enhance_phone_number_extraction(final_result, user_input)
        
        # Add processing metadata
        final_result["original_input"] = user_input
        final_result["timestamp"] = self._get_timestamp()
        
        logger.info(f"Final processed command: {final_result.get('action', 'unknown')} (confidence: {final_result.get('confidence', 0)})")
        
        return final_result
    
    def _structured_parsing(self, user_input: str) -> Dict[str, Any]:
        """
        Enhanced structured parsing with regex and keyword matching
        
        Args:
            user_input (str): User input to parse
        
        Returns:
            dict: Parsed command result
        """
        user_input_lower = user_input.lower().strip()
        best_match = None
        best_confidence = 0.0
        
        # Extract phone numbers first
        phone_numbers = self._extract_phone_numbers(user_input)
        
        for action, patterns in self.command_patterns.items():
            confidence = 0.0
            
            # Check keywords
            keyword_matches = sum(1 for keyword in patterns["keywords"] if keyword in user_input_lower)
            if keyword_matches > 0:
                confidence += (keyword_matches / len(patterns["keywords"])) * 0.6
            
            # Check regex pattern
            if re.search(patterns["regex"], user_input_lower, re.IGNORECASE):
                confidence += 0.3
            
            # Apply confidence boost
            confidence += patterns.get("confidence_boost", 0)
            
            # Special handling for phone number dependent actions
            if action in ["call_specific", "add_number", "remove_number"]:
                if phone_numbers:
                    confidence += 0.2  # Boost if phone number is present
                else:
                    confidence *= 0.3  # Reduce if no phone number found
            
            # Update best match
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    "action": action,
                    "confidence": min(confidence, 1.0),
                    "phone_numbers": phone_numbers
                }
        
        if not best_match or best_confidence < 0.3:
            return {
                "action": "unknown",
                "parameters": {},
                "confidence": 0.1,
                "explanation": "No clear action pattern detected",
                "processing_method": "structured"
            }
        
        # Build parameters based on action
        parameters = {}
        if best_match["phone_numbers"] and best_match["action"] in ["call_specific", "add_number", "remove_number"]:
            parameters["phone_number"] = best_match["phone_numbers"][0]  # Use first number found
        
        # Extract custom message if present
        message_match = re.search(r'(with message|message|say)\s*["\']?([^"\']+)["\']?', user_input, re.IGNORECASE)
        if message_match:
            parameters["message"] = message_match.group(2).strip()
        
        return {
            "action": best_match["action"],
            "parameters": parameters,
            "confidence": best_match["confidence"],
            "explanation": f"Detected {best_match['action']} command using structured parsing",
            "processing_method": "structured"
        }
    
    def _combine_parsing_results(self, gemini_result: Optional[Dict], structured_result: Dict, user_input: str) -> Dict[str, Any]:
        """
        Intelligently combine Gemini and structured parsing results
        
        Args:
            gemini_result (dict or None): Result from Gemini API
            structured_result (dict): Result from structured parsing
            user_input (str): Original user input
        
        Returns:
            dict: Combined result
        """
        # If no Gemini result, use structured
        if not gemini_result:
            structured_result["processing_method"] = "structured_only"
            return structured_result
        
        # If Gemini has high confidence and valid action, prefer it
        if (gemini_result.get("confidence", 0) >= 0.8 and 
            gemini_result.get("action") != "unknown" and
            not gemini_result.get("error")):
            gemini_result["processing_method"] = "gemini_primary"
            return gemini_result
        
        # If structured has higher confidence, use it
        if structured_result.get("confidence", 0) > gemini_result.get("confidence", 0):
            structured_result["processing_method"] = "structured_primary"
            structured_result["gemini_backup"] = gemini_result.get("action", "unknown")
            return structured_result
        
        # If both have similar confidence, prefer Gemini but validate with structured
        if abs(gemini_result.get("confidence", 0) - structured_result.get("confidence", 0)) < 0.2:
            # Use Gemini action but merge parameters
            combined_params = {**structured_result.get("parameters", {}), **gemini_result.get("parameters", {})}
            
            result = gemini_result.copy()
            result["parameters"] = combined_params
            result["processing_method"] = "combined"
            result["structured_backup"] = structured_result.get("action", "unknown")
            
            return result
        
        # Default to Gemini with structured backup
        gemini_result["processing_method"] = "gemini_with_backup"
        gemini_result["structured_backup"] = structured_result.get("action", "unknown")
        return gemini_result
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extract and validate phone numbers from text
        
        Args:
            text (str): Text to extract phone numbers from
        
        Returns:
            list: List of validated phone numbers
        """
        # Enhanced phone number patterns for Indian numbers
        patterns = [
            r'(\+91[\s-]?[6-9]\d{9})',  # +91 mobile
            r'(\+91[\s-]?1800\d{7})',   # +91 toll-free
            r'(91[\s-]?[6-9]\d{9})',    # 91 mobile
            r'(91[\s-]?1800\d{7})',     # 91 toll-free
            r'([6-9]\d{9})',            # 10-digit mobile
            r'(1800\d{7})',             # 11-digit toll-free
        ]
        
        found_numbers = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean and validate the number
                cleaned_number = re.sub(r'[\s-]', '', match)
                
                # Format to +91 format
                if cleaned_number.startswith('+91'):
                    formatted_number = cleaned_number
                elif cleaned_number.startswith('91'):
                    formatted_number = '+' + cleaned_number
                else:
                    formatted_number = '+91' + cleaned_number
                
                # Validate using the models validation function
                is_valid, result = validate_phone_number(formatted_number)
                if is_valid and result not in found_numbers:
                    found_numbers.append(result)
        
        return found_numbers
    
    def _enhance_phone_number_extraction(self, result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Enhance phone number extraction and validation
        
        Args:
            result (dict): Current parsing result
            user_input (str): Original user input
        
        Returns:
            dict: Enhanced result with validated phone numbers
        """
        # Extract all phone numbers from input
        all_numbers = self._extract_phone_numbers(user_input)
        
        # If no phone number in parameters but found in text, add it
        if not result["parameters"].get("phone_number") and all_numbers:
            result["parameters"]["phone_number"] = all_numbers[0]
            result["confidence"] = min(result.get("confidence", 0) + 0.1, 1.0)
        
        # Validate existing phone number in parameters
        if "phone_number" in result["parameters"]:
            phone_number = result["parameters"]["phone_number"]
            is_valid, validated_number = validate_phone_number(phone_number)
            
            if is_valid:
                result["parameters"]["phone_number"] = validated_number
            else:
                result["parameters"]["phone_number_error"] = f"Invalid phone number: {phone_number}"
                result["confidence"] *= 0.7  # Reduce confidence for invalid numbers
        
        # Add all found numbers for reference
        if all_numbers:
            result["parameters"]["all_phone_numbers"] = all_numbers
        
        return result
    
    def extract_phone_numbers_from_text(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Extract and categorize phone numbers from text input
        
        Args:
            text (str): Text containing phone numbers
        
        Returns:
            tuple: (valid_numbers, invalid_numbers)
        """
        # Split text into potential phone number candidates
        # Handle various separators: newlines, commas, spaces, semicolons
        candidates = re.split(r'[\n,;\s]+', text.strip())
        
        valid_numbers = []
        invalid_numbers = []
        
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate:
                continue
            
            # Try to extract phone number from the candidate
            extracted_numbers = self._extract_phone_numbers(candidate)
            
            if extracted_numbers:
                valid_numbers.extend(extracted_numbers)
            else:
                # Check if it looks like a phone number attempt
                if re.search(r'\d{7,}', candidate):
                    invalid_numbers.append(candidate)
        
        # Remove duplicates while preserving order
        valid_numbers = list(dict.fromkeys(valid_numbers))
        invalid_numbers = list(dict.fromkeys(invalid_numbers))
        
        return valid_numbers, invalid_numbers
    
    def validate_command_parameters(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate command parameters based on action type
        
        Args:
            action (str): Command action
            parameters (dict): Command parameters
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if action in ["call_specific", "add_number", "remove_number"]:
            if not parameters.get("phone_number"):
                return False, f"Phone number is required for {action} command"
            
            # Check for phone number validation errors
            if "phone_number_error" in parameters:
                return False, parameters["phone_number_error"]
        
        elif action == "call_all":
            # No specific parameters required for call_all
            pass
        
        elif action in ["view_logs", "get_statistics"]:
            # Optional parameters, no validation needed
            pass
        
        elif action == "unknown":
            return False, "Command not recognized. Please try rephrasing your request."
        
        return True, "Parameters are valid"
    
    def generate_response(self, action_result: Dict[str, Any], original_command: str) -> str:
        """
        Generate natural language response for command results
        
        Args:
            action_result (dict): Result from executing the command
            original_command (str): Original user command
        
        Returns:
            str: Natural language response
        """
        if self.gemini_processor:
            try:
                return self.gemini_processor.generate_response(action_result, original_command)
            except Exception as e:
                logger.warning(f"Gemini response generation failed: {e}")
        
        # Fallback to simple response generation
        return self._generate_simple_response(action_result, original_command)
    
    def _generate_simple_response(self, action_result: Dict[str, Any], original_command: str) -> str:
        """
        Generate simple response when Gemini is not available
        
        Args:
            action_result (dict): Result from executing the command
            original_command (str): Original user command
        
        Returns:
            str: Simple response
        """
        status = action_result.get("status", "unknown")
        action = action_result.get("action", "unknown")
        
        if status == "success":
            if action == "call_all":
                stats = action_result.get("statistics", {})
                total = stats.get("total", 0)
                return f"✅ Started calling {total} numbers. Check the progress below!"
            
            elif action == "call_specific":
                phone_number = action_result.get("phone_number", "the number")
                return f"✅ Calling {phone_number} now!"
            
            elif action == "add_number":
                phone_number = action_result.get("phone_number", "the number")
                return f"✅ Added {phone_number} to your list!"
            
            elif action == "remove_number":
                phone_number = action_result.get("phone_number", "the number")
                return f"✅ Removed {phone_number} from your list!"
            
            elif action == "view_logs":
                count = action_result.get("count", 0)
                return f"📋 Found {count} call records. Check the logs above!"
            
            elif action == "get_statistics":
                stats = action_result.get("statistics", {})
                total = stats.get("total_calls", 0)
                success_rate = stats.get("success_rate", 0)
                return f"📊 Stats: {total} calls made, {success_rate}% success rate!"
        
        elif status in ["error", "failed"]:
            error_msg = action_result.get("error", "Something went wrong")
            return f"❌ {error_msg}"
        
        return "🤔 I processed your request, but I'm not sure about the result."
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test AI processor connections
        
        Returns:
            dict: Connection test results
        """
        results = {
            "ai_processor": "initialized",
            "gemini_processor": "not_available",
            "structured_parsing": "available"
        }
        
        if self.gemini_processor:
            gemini_test = self.gemini_processor.test_connection()
            results["gemini_processor"] = gemini_test.get("status", "failed")
            results["gemini_details"] = gemini_test
        
        return {
            "status": "success",
            "components": results,
            "message": "AI Processor is ready for command processing"
        }