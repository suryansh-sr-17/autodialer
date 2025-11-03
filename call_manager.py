import os
import time
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from config import Config
from models import log_call, get_call_statistics, get_call_logs
from error_handler import (
    handle_errors,
    TwilioAPIError,
    ValidationError,
    ConfigurationError,
    error_handler,
    validate_required_fields,
    validate_phone_number_format,
    is_recoverable_error,
    get_retry_delay
)

# Set up logging
from logging_config import log_call_attempt, log_error_with_context, log_performance_metric, LoggedOperation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CallManager:
    """Manages Twilio API interactions and call orchestration"""
    
    def __init__(self, account_sid=None, auth_token=None, phone_number=None):
        """Initialize Twilio client with comprehensive credential validation and error handling"""
        try:
            # Get credentials from parameters or environment
            self.account_sid = account_sid or Config.TWILIO_ACCOUNT_SID
            self.auth_token = auth_token or Config.TWILIO_AUTH_TOKEN
            self.phone_number = phone_number or Config.TWILIO_PHONE_NUMBER
            
            # Validate required credentials
            missing_credentials = []
            if not self.account_sid:
                missing_credentials.append("TWILIO_ACCOUNT_SID")
            if not self.auth_token:
                missing_credentials.append("TWILIO_AUTH_TOKEN")
            if not self.phone_number:
                missing_credentials.append("TWILIO_PHONE_NUMBER")
            
            if missing_credentials:
                raise ConfigurationError(
                    message=f"Missing required Twilio credentials: {', '.join(missing_credentials)}",
                    details={"missing_credentials": missing_credentials}
                )
            
            # Validate credential formats
            if not self.account_sid.startswith('AC') or len(self.account_sid) != 34:
                raise ConfigurationError(
                    message="Invalid Twilio Account SID format",
                    config_key="TWILIO_ACCOUNT_SID"
                )
            
            if len(self.auth_token) != 32:
                raise ConfigurationError(
                    message="Invalid Twilio Auth Token format",
                    config_key="TWILIO_AUTH_TOKEN"
                )
            
            # Validate phone number format (Twilio numbers are exempt from test mode)
            if not self.phone_number.startswith('+'):
                raise ConfigurationError(
                    message="Twilio phone number must start with + (international format)",
                    config_key="TWILIO_PHONE_NUMBER"
                )
            
            # Basic length validation for Twilio numbers
            if len(self.phone_number) < 10 or len(self.phone_number) > 16:
                raise ConfigurationError(
                    message="Twilio phone number length invalid",
                    config_key="TWILIO_PHONE_NUMBER"
                )
            
            # Initialize Twilio client with error handling
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
                
                # Test the connection
                try:
                    account = self.client.api.accounts(self.account_sid).fetch()
                    if account.status != 'active':
                        logger.warning(f"Twilio account status: {account.status}")
                except TwilioException as e:
                    logger.warning(f"Could not verify Twilio account status: {e}")
                
            except TwilioException as e:
                raise error_handler.handle_twilio_error(e, "client_initialization")
            except Exception as e:
                raise ConfigurationError(
                    message=f"Failed to initialize Twilio client: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
            
            # Default TTS message
            self.default_message = "Hello, this is an automated call from Suryansh. Thank you"
            
            # Call tracking
            self.active_calls = {}
            self.call_statistics = {
                "total_attempts": 0,
                "successful_calls": 0,
                "failed_calls": 0
            }
            
            logger.info(f"CallManager initialized with phone number: {self.phone_number}")
            
        except (ConfigurationError, TwilioAPIError):
            raise  # Re-raise our custom errors
        except Exception as e:
            logger.error(f"Unexpected error initializing CallManager: {e}")
            raise ConfigurationError(
                message=f"CallManager initialization failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    @handle_errors(operation="make_call")
    def make_call(self, phone_number, message=None, retry_count=0, max_retries=2):
        """
        Make individual call with comprehensive error handling and retry logic
        
        Args:
            phone_number (str): Phone number to call
            message (str, optional): Custom message to deliver. Defaults to default message.
            retry_count (int): Current retry attempt
            max_retries (int): Maximum number of retries for recoverable errors
        
        Returns:
            dict: Call result with status, call_sid, and error information
        """
        try:
            # Input validation
            if not phone_number:
                raise ValidationError(
                    message="Phone number is required",
                    field="phone_number",
                    value=phone_number
                )
            
            # Validate and format phone number
            try:
                validated_number = validate_phone_number_format(phone_number)
            except ValidationError as e:
                logger.error(f"Invalid phone number format: {phone_number}")
                # Log the failed call attempt
                log_call(phone_number, None, "failed", error_message=f"Invalid format: {e.message}")
                raise
            
            # Use default message if none provided
            tts_message = message or self.default_message
            
            # Validate message length (Twilio has limits)
            if len(tts_message) > 4000:  # Twilio's character limit
                logger.warning(f"Message too long ({len(tts_message)} chars), truncating")
                tts_message = tts_message[:3997] + "..."
            
            logger.info(f"Initiating call to {validated_number} (attempt {retry_count + 1})")
            
            # Update statistics
            self.call_statistics["total_attempts"] += 1
            
            # Create TwiML URL for text-to-speech
            import urllib.parse
            encoded_message = urllib.parse.quote_plus(tts_message)
            twiml_url = f"http://twimlets.com/message?Message%5B0%5D={encoded_message}"
            
            # Make the call with timeout
            try:
                call = self.client.calls.create(
                    to=validated_number,
                    from_=self.phone_number,
                    url=twiml_url,
                    method='GET',
                    timeout=30,  # 30 second timeout
                    record=False  # Don't record calls by default
                )
                
                logger.info(f"Call initiated successfully. SID: {call.sid}")
                
                # Track active call
                self.active_calls[call.sid] = {
                    "phone_number": validated_number,
                    "start_time": time.time(),
                    "message": tts_message
                }
                
                # Log the successful call initiation
                log_call(validated_number, call.sid, "initiated")
                log_call_attempt(validated_number, call.sid, "initiated", 
                               message_length=len(tts_message), retry_count=retry_count)
                
                # Update statistics
                self.call_statistics["successful_calls"] += 1
                
                return {
                    "status": "success",
                    "call_sid": call.sid,
                    "error": None,
                    "phone_number": validated_number,
                    "message": tts_message,
                    "retry_count": retry_count
                }
                
            except TwilioException as e:
                # Handle specific Twilio errors
                twilio_error = error_handler.handle_twilio_error(
                    e, "make_call", validated_number
                )
                
                # Check if error is recoverable and we haven't exceeded retries
                if (retry_count < max_retries and 
                    is_recoverable_error(e) and 
                    getattr(e, 'code', None) not in [21211, 21212, 21214]):  # Don't retry invalid numbers
                    
                    delay = get_retry_delay(retry_count + 1)
                    logger.warning(f"Recoverable error, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                    
                    return self.make_call(
                        phone_number=validated_number,
                        message=message,
                        retry_count=retry_count + 1,
                        max_retries=max_retries
                    )
                
                # Log the failed call
                log_call(validated_number, None, "failed", error_message=twilio_error.message)
                log_call_attempt(validated_number, None, "failed", 
                               error=twilio_error.message, retry_count=retry_count,
                               twilio_error_code=getattr(e, 'code', None))
                
                # Update statistics
                self.call_statistics["failed_calls"] += 1
                
                return {
                    "status": "failed",
                    "call_sid": None,
                    "error": twilio_error.message,
                    "error_code": twilio_error.error_code,
                    "phone_number": validated_number,
                    "retry_count": retry_count,
                    "twilio_error_code": getattr(e, 'code', None)
                }
        
        except ValidationError as e:
            logger.error(f"Validation error for call to {phone_number}: {e.message}")
            return {
                "status": "failed",
                "call_sid": None,
                "error": e.message,
                "error_code": e.error_code,
                "phone_number": phone_number,
                "retry_count": retry_count
            }
        
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error making call to {phone_number}: {str(e)}"
            logger.error(error_msg)
            
            # Log the failed call
            try:
                log_call(phone_number, None, "failed", error_message=error_msg)
            except Exception as log_error:
                logger.error(f"Failed to log call error: {log_error}")
            
            # Update statistics
            self.call_statistics["failed_calls"] += 1
            
            return {
                "status": "failed",
                "call_sid": None,
                "error": error_msg,
                "error_code": "UNEXPECTED_ERROR",
                "phone_number": phone_number,
                "retry_count": retry_count
            }
    
    def get_call_status(self, call_sid):
        """
        Get the current status of a call
        
        Args:
            call_sid (str): Twilio call SID
        
        Returns:
            dict: Call status information
        """
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                "status": "success",
                "call_status": call.status,
                "duration": call.duration,
                "start_time": call.start_time,
                "end_time": call.end_time,
                "error": None
            }
            
        except TwilioException as e:
            error_msg = f"Failed to fetch call status: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "failed",
                "call_status": None,
                "duration": None,
                "start_time": None,
                "end_time": None,
                "error": error_msg
            }
    
    def validate_phone_number(self, phone_number):
        """
        Validate phone number using Twilio's lookup API
        
        Args:
            phone_number (str): Phone number to validate
        
        Returns:
            dict: Validation result
        """
        try:
            # Use Twilio's lookup service to validate the number
            phone_number_info = self.client.lookups.v1.phone_numbers(phone_number).fetch()
            
            return {
                "status": "valid",
                "formatted_number": phone_number_info.phone_number,
                "country_code": phone_number_info.country_code,
                "error": None
            }
            
        except TwilioException as e:
            error_msg = f"Phone number validation failed: {str(e)}"
            logger.warning(error_msg)
            
            return {
                "status": "invalid",
                "formatted_number": None,
                "country_code": None,
                "error": error_msg
            }
    
    def bulk_call(self, phone_numbers, message=None, delay_between_calls=2):
        """
        Create sequential calling method that processes number lists
        
        Args:
            phone_numbers (list): List of phone numbers to call
            message (str, optional): Custom message to deliver. Defaults to default message.
            delay_between_calls (int): Delay in seconds between calls. Defaults to 2.
        
        Returns:
            dict: Bulk calling results with detailed statistics
        """
        if not phone_numbers or not isinstance(phone_numbers, list):
            error_msg = "Phone numbers list is required and must be a list"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "results": [],
                "statistics": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "success_rate": 0
                }
            }
        
        logger.info(f"Starting bulk calling for {len(phone_numbers)} numbers")
        
        results = []
        successful_calls = 0
        failed_calls = 0
        
        for i, phone_number in enumerate(phone_numbers):
            try:
                logger.info(f"Processing call {i+1}/{len(phone_numbers)}: {phone_number}")
                
                # Make the call
                call_result = self.make_call(phone_number, message)
                results.append(call_result)
                
                # Track statistics
                if call_result["status"] == "success":
                    successful_calls += 1
                    logger.info(f"Call {i+1} successful: {phone_number}")
                else:
                    failed_calls += 1
                    logger.warning(f"Call {i+1} failed: {phone_number} - {call_result.get('error', 'Unknown error')}")
                
                # Add delay between calls (except for the last call)
                if i < len(phone_numbers) - 1:
                    logger.info(f"Waiting {delay_between_calls} seconds before next call...")
                    time.sleep(delay_between_calls)
                
            except Exception as e:
                error_msg = f"Unexpected error processing {phone_number}: {str(e)}"
                logger.error(error_msg)
                
                # Add failed result
                failed_result = {
                    "status": "failed",
                    "call_sid": None,
                    "error": error_msg,
                    "phone_number": phone_number
                }
                results.append(failed_result)
                failed_calls += 1
                
                # Log the failed call
                log_call(phone_number, None, "failed", error_message=error_msg)
        
        # Calculate statistics
        total_calls = len(phone_numbers)
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        statistics = {
            "total": total_calls,
            "successful": successful_calls,
            "failed": failed_calls,
            "success_rate": round(success_rate, 2)
        }
        
        logger.info(f"Bulk calling completed. Success rate: {success_rate:.2f}% ({successful_calls}/{total_calls})")
        
        return {
            "status": "completed",
            "error": None,
            "results": results,
            "statistics": statistics
        }
    
    def bulk_call_with_status_tracking(self, phone_numbers, message=None, delay_between_calls=2, status_callback=None):
        """
        Bulk calling with real-time status tracking and callback support
        
        Args:
            phone_numbers (list): List of phone numbers to call
            message (str, optional): Custom message to deliver
            delay_between_calls (int): Delay in seconds between calls
            status_callback (callable, optional): Callback function for status updates
        
        Returns:
            dict: Bulk calling results with enhanced tracking
        """
        if not phone_numbers or not isinstance(phone_numbers, list):
            error_msg = "Phone numbers list is required and must be a list"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "results": [],
                "statistics": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "in_progress": 0,
                    "success_rate": 0
                }
            }
        
        logger.info(f"Starting bulk calling with status tracking for {len(phone_numbers)} numbers")
        
        results = []
        successful_calls = 0
        failed_calls = 0
        in_progress_calls = 0
        
        for i, phone_number in enumerate(phone_numbers):
            try:
                # Notify callback of current progress
                if status_callback:
                    status_callback({
                        "current_number": i + 1,
                        "total_numbers": len(phone_numbers),
                        "phone_number": phone_number,
                        "status": "calling"
                    })
                
                logger.info(f"Processing call {i+1}/{len(phone_numbers)}: {phone_number}")
                
                # Make the call
                call_result = self.make_call(phone_number, message)
                
                # Enhanced result tracking
                call_result["call_index"] = i + 1
                call_result["timestamp"] = time.time()
                results.append(call_result)
                
                # Track statistics
                if call_result["status"] == "success":
                    successful_calls += 1
                    in_progress_calls += 1  # Call is initiated but may still be in progress
                    logger.info(f"Call {i+1} initiated successfully: {phone_number}")
                    
                    # Notify callback of success
                    if status_callback:
                        status_callback({
                            "current_number": i + 1,
                            "total_numbers": len(phone_numbers),
                            "phone_number": phone_number,
                            "status": "success",
                            "call_sid": call_result["call_sid"]
                        })
                else:
                    failed_calls += 1
                    logger.warning(f"Call {i+1} failed: {phone_number} - {call_result.get('error', 'Unknown error')}")
                    
                    # Notify callback of failure
                    if status_callback:
                        status_callback({
                            "current_number": i + 1,
                            "total_numbers": len(phone_numbers),
                            "phone_number": phone_number,
                            "status": "failed",
                            "error": call_result.get("error")
                        })
                
                # Add delay between calls (except for the last call)
                if i < len(phone_numbers) - 1:
                    logger.info(f"Waiting {delay_between_calls} seconds before next call...")
                    time.sleep(delay_between_calls)
                
            except Exception as e:
                error_msg = f"Unexpected error processing {phone_number}: {str(e)}"
                logger.error(error_msg)
                
                # Add failed result
                failed_result = {
                    "status": "failed",
                    "call_sid": None,
                    "error": error_msg,
                    "phone_number": phone_number,
                    "call_index": i + 1,
                    "timestamp": time.time()
                }
                results.append(failed_result)
                failed_calls += 1
                
                # Log the failed call
                log_call(phone_number, None, "failed", error_message=error_msg)
                
                # Notify callback of error
                if status_callback:
                    status_callback({
                        "current_number": i + 1,
                        "total_numbers": len(phone_numbers),
                        "phone_number": phone_number,
                        "status": "error",
                        "error": error_msg
                    })
        
        # Calculate final statistics
        total_calls = len(phone_numbers)
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        statistics = {
            "total": total_calls,
            "successful": successful_calls,
            "failed": failed_calls,
            "in_progress": in_progress_calls,
            "success_rate": round(success_rate, 2)
        }
        
        logger.info(f"Bulk calling completed. Success rate: {success_rate:.2f}% ({successful_calls}/{total_calls})")
        
        # Final callback notification
        if status_callback:
            status_callback({
                "status": "completed",
                "statistics": statistics
            })
        
        return {
            "status": "completed",
            "error": None,
            "results": results,
            "statistics": statistics
        }
    
    def process_call_results(self, call_sids, update_database=True):
        """
        Process Twilio call responses and extract status information
        
        Args:
            call_sids (list): List of Twilio call SIDs to process
            update_database (bool): Whether to update database with results
        
        Returns:
            dict: Processed call results with detailed status information
        """
        if not call_sids or not isinstance(call_sids, list):
            error_msg = "Call SIDs list is required and must be a list"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "processed_calls": []
            }
        
        logger.info(f"Processing {len(call_sids)} call results")
        
        processed_calls = []
        
        for call_sid in call_sids:
            try:
                # Fetch call details from Twilio
                call = self.client.calls(call_sid).fetch()
                
                # Extract call information
                call_info = {
                    "call_sid": call.sid,
                    "phone_number": call.to,
                    "from_number": call.from_,
                    "status": call.status,
                    "duration": call.duration or 0,
                    "start_time": call.start_time,
                    "end_time": call.end_time,
                    "direction": call.direction,
                    "answered_by": getattr(call, 'answered_by', None),
                    "price": getattr(call, 'price', None),
                    "price_unit": getattr(call, 'price_unit', None),
                    "error_code": getattr(call, 'error_code', None),
                    "error_message": getattr(call, 'error_message', None)
                }
                
                # Map Twilio status to our internal status
                internal_status = self._map_twilio_status(call.status)
                call_info["internal_status"] = internal_status
                
                processed_calls.append(call_info)
                
                # Update database if requested
                if update_database:
                    error_msg = call_info.get("error_message")
                    if call_info.get("error_code"):
                        error_msg = f"Error {call_info['error_code']}: {error_msg or 'Unknown error'}"
                    
                    log_call(
                        phone_number=call_info["phone_number"],
                        call_sid=call_info["call_sid"],
                        status=internal_status,
                        duration=call_info["duration"],
                        error_message=error_msg
                    )
                
                logger.info(f"Processed call {call_sid}: {internal_status}")
                
            except TwilioException as e:
                error_msg = f"Failed to fetch call details for {call_sid}: {str(e)}"
                logger.error(error_msg)
                
                error_info = {
                    "call_sid": call_sid,
                    "phone_number": "unknown",
                    "status": "error",
                    "internal_status": "failed",
                    "duration": 0,
                    "error_message": error_msg
                }
                processed_calls.append(error_info)
                
                # Update database with error
                if update_database:
                    log_call(
                        phone_number="unknown",
                        call_sid=call_sid,
                        status="failed",
                        error_message=error_msg
                    )
            
            except Exception as e:
                error_msg = f"Unexpected error processing call {call_sid}: {str(e)}"
                logger.error(error_msg)
                
                error_info = {
                    "call_sid": call_sid,
                    "phone_number": "unknown",
                    "status": "error",
                    "internal_status": "failed",
                    "duration": 0,
                    "error_message": error_msg
                }
                processed_calls.append(error_info)
        
        logger.info(f"Completed processing {len(processed_calls)} call results")
        
        return {
            "status": "success",
            "error": None,
            "processed_calls": processed_calls
        }
    
    def _map_twilio_status(self, twilio_status):
        """
        Map Twilio call status to internal status
        
        Args:
            twilio_status (str): Twilio call status
        
        Returns:
            str: Internal status mapping
        """
        status_mapping = {
            "completed": "completed",
            "answered": "completed",
            "busy": "busy",
            "no-answer": "no-answer",
            "failed": "failed",
            "canceled": "canceled",
            "queued": "queued",
            "ringing": "ringing",
            "in-progress": "in-progress"
        }
        
        return status_mapping.get(twilio_status.lower(), "unknown")
    
    def update_call_statuses(self, call_sids_with_numbers):
        """
        Update call statuses for a list of calls and store results in database
        
        Args:
            call_sids_with_numbers (list): List of dicts with call_sid and phone_number
        
        Returns:
            dict: Updated call status results
        """
        if not call_sids_with_numbers or not isinstance(call_sids_with_numbers, list):
            error_msg = "Call SIDs with numbers list is required"
            logger.error(error_msg)
            return {
                "status": "failed",
                "error": error_msg,
                "updated_calls": []
            }
        
        logger.info(f"Updating status for {len(call_sids_with_numbers)} calls")
        
        updated_calls = []
        
        for call_info in call_sids_with_numbers:
            call_sid = call_info.get("call_sid")
            phone_number = call_info.get("phone_number")
            
            if not call_sid or not phone_number:
                logger.warning(f"Skipping invalid call info: {call_info}")
                continue
            
            try:
                # Get current call status
                status_result = self.get_call_status(call_sid)
                
                if status_result["status"] == "success":
                    call_status = status_result["call_status"]
                    duration = status_result["duration"] or 0
                    
                    # Map to internal status
                    internal_status = self._map_twilio_status(call_status)
                    
                    # Update database
                    log_call(
                        phone_number=phone_number,
                        call_sid=call_sid,
                        status=internal_status,
                        duration=duration
                    )
                    
                    updated_call = {
                        "call_sid": call_sid,
                        "phone_number": phone_number,
                        "status": internal_status,
                        "duration": duration,
                        "twilio_status": call_status
                    }
                    updated_calls.append(updated_call)
                    
                    logger.info(f"Updated call status: {call_sid} -> {internal_status}")
                
                else:
                    error_msg = status_result.get("error", "Unknown error")
                    logger.error(f"Failed to get status for call {call_sid}: {error_msg}")
                    
                    # Log as failed
                    log_call(
                        phone_number=phone_number,
                        call_sid=call_sid,
                        status="failed",
                        error_message=error_msg
                    )
            
            except Exception as e:
                error_msg = f"Error updating call status for {call_sid}: {str(e)}"
                logger.error(error_msg)
                
                # Log as failed
                log_call(
                    phone_number=phone_number,
                    call_sid=call_sid,
                    status="failed",
                    error_message=error_msg
                )
        
        logger.info(f"Updated {len(updated_calls)} call statuses")
        
        return {
            "status": "success",
            "error": None,
            "updated_calls": updated_calls
        }
    
    def get_call_statistics_summary(self, phone_number=None, days=None):
        """
        Get comprehensive call statistics from database
        
        Args:
            phone_number (str, optional): Filter by specific phone number
            days (int, optional): Filter by number of days
        
        Returns:
            dict: Call statistics summary
        """
        try:
            # Get statistics from database
            stats = get_call_statistics(phone_number=phone_number, days=days)
            
            if not stats:
                logger.warning("No call statistics found")
                return {
                    "status": "success",
                    "statistics": {
                        "total_calls": 0,
                        "successful_calls": 0,
                        "failed_calls": 0,
                        "success_rate": 0,
                        "average_duration": 0
                    }
                }
            
            # Add additional calculated metrics
            enhanced_stats = {
                **stats,
                "completion_rate": stats.get("success_rate", 0),
                "failure_rate": stats.get("failure_rate", 0),
                "average_duration_minutes": round((stats.get("avg_duration", 0) / 60), 2) if stats.get("avg_duration") else 0,
                "total_duration_minutes": round((stats.get("total_duration", 0) / 60), 2) if stats.get("total_duration") else 0
            }
            
            logger.info(f"Retrieved call statistics: {enhanced_stats['total_calls']} total calls")
            
            return {
                "status": "success",
                "error": None,
                "statistics": enhanced_stats
            }
            
        except Exception as e:
            error_msg = f"Error retrieving call statistics: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "failed",
                "error": error_msg,
                "statistics": {}
            }
    
    def get_recent_call_logs(self, limit=50, phone_number=None, status=None):
        """
        Get recent call logs with optional filtering
        
        Args:
            limit (int): Maximum number of logs to retrieve
            phone_number (str, optional): Filter by phone number
            status (str, optional): Filter by call status
        
        Returns:
            dict: Recent call logs
        """
        try:
            # Get call logs from database
            logs = get_call_logs(limit=limit, phone_number=phone_number, status=status)
            
            logger.info(f"Retrieved {len(logs)} call logs")
            
            return {
                "status": "success",
                "error": None,
                "call_logs": logs,
                "count": len(logs)
            }
            
        except Exception as e:
            error_msg = f"Error retrieving call logs: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "failed",
                "error": error_msg,
                "call_logs": [],
                "count": 0
            }
    
    def test_connection(self):
        """
        Test Twilio connection by fetching account information
        
        Returns:
            dict: Connection test result
        """
        try:
            account = self.client.api.accounts(self.account_sid).fetch()
            
            logger.info("Twilio connection test successful")
            
            return {
                "status": "success",
                "account_sid": account.sid,
                "account_status": account.status,
                "error": None
            }
            
        except TwilioException as e:
            error_msg = f"Twilio connection test failed: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "failed",
                "account_sid": None,
                "account_status": None,
                "error": error_msg
            }