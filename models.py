import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager
from config import Config
from error_handler import (
    handle_errors, 
    DatabaseError, 
    ValidationError,
    error_handler,
    validate_required_fields,
    log_error_context
)

DATABASE_PATH = 'autodialer.db'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection with proper configuration and error handling"""
    try:
        if not os.path.exists(DATABASE_PATH):
            logger.info(f"Database file {DATABASE_PATH} does not exist, will be created")
        
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        
        # Enable foreign key constraints
        conn.execute('PRAGMA foreign_keys = ON')
        
        # Set journal mode for better concurrency
        conn.execute('PRAGMA journal_mode = WAL')
        
        # Test the connection
        conn.execute('SELECT 1').fetchone()
        
        return conn
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e).lower():
            raise DatabaseError(
                message="Database is currently locked by another process",
                operation="get_connection",
                details={"database_path": DATABASE_PATH}
            )
        elif "disk" in str(e).lower():
            raise DatabaseError(
                message="Database disk error - check available space",
                operation="get_connection",
                details={"database_path": DATABASE_PATH}
            )
        else:
            raise DatabaseError(
                message=f"Database operational error: {str(e)}",
                operation="get_connection",
                details={"database_path": DATABASE_PATH}
            )
    except sqlite3.DatabaseError as e:
        raise DatabaseError(
            message=f"Database connection failed: {str(e)}",
            operation="get_connection",
            details={"database_path": DATABASE_PATH}
        )
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {e}")
        raise DatabaseError(
            message=f"Unexpected database connection error: {str(e)}",
            operation="get_connection",
            details={"database_path": DATABASE_PATH}
        )

@contextmanager
def get_db_transaction():
    """Context manager for database transactions with comprehensive error handling"""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
        conn.commit()
        logger.debug("Database transaction committed successfully")
    except sqlite3.IntegrityError as e:
        if conn:
            conn.rollback()
        logger.error(f"Database integrity error in transaction: {e}")
        raise error_handler.handle_database_error(e, "transaction")
    except sqlite3.OperationalError as e:
        if conn:
            conn.rollback()
        logger.error(f"Database operational error in transaction: {e}")
        raise error_handler.handle_database_error(e, "transaction")
    except sqlite3.DatabaseError as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error in transaction: {e}")
        raise error_handler.handle_database_error(e, "transaction")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in database transaction: {e}")
        raise error_handler.handle_generic_error(e, "database_transaction")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")

@handle_errors(operation="database_initialization", return_dict=False)
def init_db():
    """Initialize SQLite database with required tables and comprehensive error handling"""
    logger.info("Initializing database...")
    
    try:
        with get_db_transaction() as conn:
            # Create phone_numbers table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS phone_numbers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number TEXT UNIQUE NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT valid_number CHECK (length(number) >= 10)
                )
            ''')
            
            # Create call_logs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    call_sid TEXT,
                    status TEXT NOT NULL,
                    duration INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT valid_status CHECK (status IN ('initiated', 'completed', 'failed', 'busy', 'no-answer', 'canceled', 'queued', 'ringing', 'in-progress')),
                    CONSTRAINT valid_duration CHECK (duration >= 0)
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_phone_numbers_number ON phone_numbers(number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_phone_numbers_added_at ON phone_numbers(added_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_call_logs_phone_number ON call_logs(phone_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_call_logs_created_at ON call_logs(created_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_call_logs_call_sid ON call_logs(call_sid)')
            
            # Verify tables were created
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            expected_tables = {'phone_numbers', 'call_logs'}
            actual_tables = {row['name'] for row in tables}
            
            if not expected_tables.issubset(actual_tables):
                missing_tables = expected_tables - actual_tables
                raise DatabaseError(
                    message=f"Failed to create required tables: {missing_tables}",
                    operation="table_creation"
                )
            
            logger.info("Database initialized successfully")
            print("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"Database initialization error: {e}")
        raise

def validate_phone_number(number):
    """Validate phone number format for Indian numbers and test numbers with enhanced error handling"""
    import re
    
    try:
        # Input validation
        if number is None:
            return False, "Phone number cannot be None"
        
        if not isinstance(number, str):
            return False, f"Phone number must be a string, got {type(number).__name__}"
        
        if not number.strip():
            return False, "Phone number cannot be empty"
        
        # Clean the number (remove spaces, dashes, etc.)
        cleaned_number = re.sub(r'[^\d+]', '', number.strip())
        
        if not cleaned_number:
            return False, "Phone number contains no valid digits"
        
        # Length validation
        if len(cleaned_number) < 10:
            return False, f"Phone number too short: {len(cleaned_number)} digits (minimum 10)"
        
        if len(cleaned_number) > 15:
            return False, f"Phone number too long: {len(cleaned_number)} digits (maximum 15)"
        
        # Test mode validation - only allow 1800 numbers
        # Check current test mode setting dynamically
        import os
        from dotenv import load_dotenv
        load_dotenv()  # Ensure .env is loaded
        current_test_mode = os.getenv('TEST_MODE', 'True').lower() == 'true'
        if current_test_mode:
            # Check if it's a 1800 number (toll-free)
            if '1800' in cleaned_number:
                # Extract the 1800 part and validate
                if re.search(r'1800\d{7}', cleaned_number):
                    # Normalize format - always add +91 prefix for 1800 numbers
                    if cleaned_number.startswith('+91'):
                        return True, cleaned_number
                    elif cleaned_number.startswith('91'):
                        return True, '+' + cleaned_number
                    else:
                        return True, '+91' + cleaned_number
            
            return False, "In test mode, only 1800 XXXX XXXX numbers are allowed (e.g., +918001234567)"
        
        # Indian phone number validation patterns
        patterns = [
            (r'^(\+91|91)?[6-9]\d{9}$', "mobile"),      # Mobile numbers
            (r'^(\+91|91)?1800\d{7}$', "toll-free"),    # Toll-free numbers
            (r'^(\+91|91)?\d{2,4}\d{6,8}$', "landline") # Landline numbers
        ]
        
        for pattern, number_type in patterns:
            if re.match(pattern, cleaned_number):
                # Normalize to +91 format
                if cleaned_number.startswith('+91'):
                    normalized = cleaned_number
                elif cleaned_number.startswith('91'):
                    normalized = '+' + cleaned_number
                else:
                    normalized = '+91' + cleaned_number
                
                # Additional validation for mobile numbers
                if number_type == "mobile":
                    # Check if it's a valid mobile prefix
                    mobile_digit = normalized[3]  # First digit after +91
                    if mobile_digit not in '6789':
                        return False, f"Invalid mobile number prefix: {mobile_digit} (must be 6, 7, 8, or 9)"
                
                logger.debug(f"Validated {number_type} number: {number} -> {normalized}")
                return True, normalized
        
        # If no pattern matches, provide specific error
        if cleaned_number.startswith('+91') or cleaned_number.startswith('91'):
            return False, "Invalid Indian phone number format - check digits after country code"
        else:
            return False, "Invalid phone number format - must be Indian number (+91 XXXXX XXXXX)"
    
    except Exception as e:
        logger.error(f"Error validating phone number '{number}': {e}")
        return False, f"Phone number validation error: {str(e)}"

@handle_errors(operation="add_phone_number")
def add_phone_number(number):
    """Add a phone number to the database with comprehensive validation and error handling"""
    try:
        # Input validation
        if not number:
            raise ValidationError(
                message="Phone number is required",
                field="number",
                value=number
            )
        
        # Validate the phone number format
        is_valid, result = validate_phone_number(number)
        if not is_valid:
            logger.warning(f"Invalid phone number rejected: {number} - {result}")
            raise ValidationError(
                message=result,
                field="number",
                value=number
            )
        
        normalized_number = result
        
        # Check if number already exists (more efficient than catching IntegrityError)
        if phone_number_exists(normalized_number):
            logger.info(f"Phone number already exists: {normalized_number}")
            return {
                "status": "error",
                "message": "Phone number already exists",
                "number": normalized_number,
                "error_code": "DUPLICATE_NUMBER"
            }
        
        # Add to database
        with get_db_transaction() as conn:
            cursor = conn.execute(
                'INSERT INTO phone_numbers (number) VALUES (?)',
                (normalized_number,)
            )
            
            if cursor.rowcount != 1:
                raise DatabaseError(
                    message="Failed to insert phone number - no rows affected",
                    operation="insert_phone_number"
                )
            
            logger.info(f"Phone number added successfully: {normalized_number}")
            
            return {
                "status": "success",
                "message": "Phone number added successfully",
                "number": normalized_number,
                "id": cursor.lastrowid
            }
    
    except ValidationError:
        raise  # Re-raise validation errors
    except DatabaseError:
        raise  # Re-raise database errors
    except Exception as e:
        log_error_context("add_phone_number", {
            "input_number": number,
            "error": str(e)
        })
        raise error_handler.handle_generic_error(e, "add_phone_number")

def add_multiple_phone_numbers(numbers):
    """Add multiple phone numbers to the database"""
    results = {
        'added': [],
        'duplicates': [],
        'invalid': [],
        'errors': []
    }
    
    for number in numbers:
        is_valid, result = validate_phone_number(number)
        if not is_valid:
            results['invalid'].append({'number': number, 'error': result})
            continue
        
        normalized_number = result
        add_result = add_phone_number(normalized_number)
        
        if add_result.get('status') == 'success':
            results['added'].append(normalized_number)
        elif add_result.get('error_code') == 'DUPLICATE_NUMBER':
            results['duplicates'].append(normalized_number)
        else:
            results['errors'].append({'number': normalized_number, 'error': add_result.get('message', 'Unknown error')})
    
    return results

def get_all_phone_numbers():
    """Get all phone numbers from the database"""
    with get_db_transaction() as conn:
        try:
            numbers = conn.execute(
                'SELECT * FROM phone_numbers ORDER BY added_at DESC'
            ).fetchall()
            return [dict(row) for row in numbers]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving phone numbers: {e}")
            return []

def get_phone_number_count():
    """Get total count of phone numbers"""
    with get_db_transaction() as conn:
        try:
            result = conn.execute('SELECT COUNT(*) as count FROM phone_numbers').fetchone()
            return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting phone number count: {e}")
            return 0

def phone_number_exists(number):
    """Check if a phone number exists in the database"""
    is_valid, result = validate_phone_number(number)
    if not is_valid:
        return False
    
    normalized_number = result
    
    with get_db_transaction() as conn:
        try:
            result = conn.execute(
                'SELECT COUNT(*) as count FROM phone_numbers WHERE number = ?',
                (normalized_number,)
            ).fetchone()
            return result['count'] > 0 if result else False
        except sqlite3.Error as e:
            logger.error(f"Error checking phone number existence: {e}")
            return False

def remove_phone_number(number):
    """Remove a phone number from the database"""
    is_valid, result = validate_phone_number(number)
    if not is_valid:
        return False, result
    
    normalized_number = result
    
    with get_db_transaction() as conn:
        try:
            cursor = conn.execute(
                'DELETE FROM phone_numbers WHERE number = ?',
                (normalized_number,)
            )
            if cursor.rowcount > 0:
                logger.info(f"Phone number removed successfully: {normalized_number}")
                return True, "Phone number removed successfully"
            else:
                return False, "Phone number not found"
        except sqlite3.Error as e:
            logger.error(f"Error removing phone number: {e}")
            return False, f"Database error: {str(e)}"

def clear_all_phone_numbers():
    """Remove all phone numbers from the database"""
    with get_db_transaction() as conn:
        try:
            cursor = conn.execute('DELETE FROM phone_numbers')
            count = cursor.rowcount
            logger.info(f"Cleared {count} phone numbers from database")
            return True, f"Removed {count} phone numbers"
        except sqlite3.Error as e:
            logger.error(f"Error clearing phone numbers: {e}")
            return False, f"Database error: {str(e)}"

def log_call(phone_number, call_sid, status, duration=0, error_message=None):
    """Log a call attempt to the database"""
    with get_db_transaction() as conn:
        try:
            conn.execute(
                '''INSERT INTO call_logs 
                   (phone_number, call_sid, status, duration, error_message) 
                   VALUES (?, ?, ?, ?, ?)''',
                (phone_number, call_sid, status, duration, error_message)
            )
            logger.info(f"Call logged: {phone_number} - {status}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging call: {e}")
            return False

def get_call_logs(limit=100, phone_number=None, status=None):
    """Get call logs from the database with optional filtering"""
    with get_db_transaction() as conn:
        try:
            query = 'SELECT * FROM call_logs'
            params = []
            conditions = []
            
            if phone_number:
                conditions.append('phone_number = ?')
                params.append(phone_number)
            
            if status:
                conditions.append('status = ?')
                params.append(status)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            logs = conn.execute(query, params).fetchall()
            return [dict(row) for row in logs]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving call logs: {e}")
            return []

def get_call_logs_by_date_range(start_date, end_date, limit=100):
    """Get call logs within a specific date range"""
    with get_db_transaction() as conn:
        try:
            logs = conn.execute(
                '''SELECT * FROM call_logs 
                   WHERE created_at BETWEEN ? AND ?
                   ORDER BY created_at DESC 
                   LIMIT ?''',
                (start_date, end_date, limit)
            ).fetchall()
            return [dict(row) for row in logs]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving call logs by date range: {e}")
            return []

def get_call_statistics(phone_number=None, days=None):
    """Get call statistics from the database with optional filtering"""
    with get_db_transaction() as conn:
        try:
            query = '''
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_calls,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_calls,
                    SUM(CASE WHEN status = 'no-answer' THEN 1 ELSE 0 END) as no_answer_calls,
                    SUM(CASE WHEN status = 'busy' THEN 1 ELSE 0 END) as busy_calls,
                    SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled_calls,
                    AVG(duration) as avg_duration,
                    SUM(duration) as total_duration,
                    MAX(duration) as max_duration,
                    MIN(duration) as min_duration
                FROM call_logs
            '''
            
            params = []
            conditions = []
            
            if phone_number:
                conditions.append('phone_number = ?')
                params.append(phone_number)
            
            if days:
                conditions.append("created_at >= datetime('now', '-{} days')".format(days))
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            stats = conn.execute(query, params).fetchone()
            
            if stats:
                result = dict(stats)
                # Calculate success rate
                total = result['total_calls']
                if total > 0:
                    result['success_rate'] = round((result['successful_calls'] / total) * 100, 2)
                    result['failure_rate'] = round((result['failed_calls'] / total) * 100, 2)
                    result['no_answer_rate'] = round((result['no_answer_calls'] / total) * 100, 2)
                else:
                    result['success_rate'] = 0
                    result['failure_rate'] = 0
                    result['no_answer_rate'] = 0
                
                # Format duration values
                result['avg_duration'] = round(result['avg_duration'] or 0, 2)
                result['total_duration'] = result['total_duration'] or 0
                result['max_duration'] = result['max_duration'] or 0
                result['min_duration'] = result['min_duration'] or 0
                
                return result
            else:
                return {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'no_answer_calls': 0,
                    'busy_calls': 0,
                    'canceled_calls': 0,
                    'avg_duration': 0,
                    'total_duration': 0,
                    'max_duration': 0,
                    'min_duration': 0,
                    'success_rate': 0,
                    'failure_rate': 0,
                    'no_answer_rate': 0
                }
        except sqlite3.Error as e:
            logger.error(f"Error retrieving call statistics: {e}")
            return {}

def get_daily_call_statistics(days=7):
    """Get daily call statistics for the last N days"""
    with get_db_transaction() as conn:
        try:
            stats = conn.execute('''
                SELECT 
                    DATE(created_at) as call_date,
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_calls,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_calls,
                    AVG(duration) as avg_duration
                FROM call_logs 
                WHERE created_at >= datetime('now', '-{} days')
                GROUP BY DATE(created_at)
                ORDER BY call_date DESC
            '''.format(days)).fetchall()
            
            return [dict(row) for row in stats]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving daily call statistics: {e}")
            return []

def clear_call_logs(older_than_days=None):
    """Clear call logs, optionally only those older than specified days"""
    with get_db_transaction() as conn:
        try:
            if older_than_days:
                cursor = conn.execute(
                    "DELETE FROM call_logs WHERE created_at < datetime('now', '-{} days')".format(older_than_days)
                )
            else:
                cursor = conn.execute('DELETE FROM call_logs')
            
            count = cursor.rowcount
            logger.info(f"Cleared {count} call logs from database")
            return True, f"Removed {count} call logs"
        except sqlite3.Error as e:
            logger.error(f"Error clearing call logs: {e}")
            return False, f"Database error: {str(e)}"

def get_call_status_summary():
    """Get a summary of call statuses"""
    with get_db_transaction() as conn:
        try:
            summary = conn.execute('''
                SELECT 
                    status,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM call_logs), 2) as percentage
                FROM call_logs 
                GROUP BY status
                ORDER BY count DESC
            ''').fetchall()
            
            return [dict(row) for row in summary]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving call status summary: {e}")
            return []