"""
Simplified models for serverless deployment
"""

import sqlite3
import re
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# In-memory database connection
_db_connection = None

def get_db_connection():
    """Get or create database connection"""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(':memory:', check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row
        init_db()
    return _db_connection

def init_db():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create phone_numbers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create call_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT NOT NULL,
                call_sid TEXT,
                status TEXT,
                duration INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def validate_phone_number(phone_number: str) -> Tuple[bool, str]:
    """Validate and format phone number"""
    try:
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone_number.strip())
        
        if not cleaned:
            return False, "Empty phone number"
        
        # Check for Indian mobile number patterns
        patterns = [
            r'^\+91[6-9]\d{9}$',      # +91 followed by 10 digits starting with 6-9
            r'^91[6-9]\d{9}$',        # 91 followed by 10 digits starting with 6-9
            r'^[6-9]\d{9}$',          # 10 digits starting with 6-9
            r'^\+911800\d{7}$',       # Test numbers: +911800XXXXXXX
            r'^911800\d{7}$',         # Test numbers: 911800XXXXXXX
            r'^1800\d{7}$'            # Test numbers: 1800XXXXXXX
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned):
                # Format to standard +91 format
                if cleaned.startswith('+91'):
                    return True, cleaned
                elif cleaned.startswith('91'):
                    return True, '+' + cleaned
                elif cleaned.startswith('1800'):
                    return True, '+91' + cleaned
                else:
                    return True, '+91' + cleaned
        
        return False, "Invalid phone number format"
        
    except Exception as e:
        logger.error(f"Phone number validation error: {e}")
        return False, f"Validation error: {str(e)}"

def add_phone_number(phone_number: str) -> Dict:
    """Add a phone number to the database"""
    try:
        # Validate the phone number
        is_valid, result = validate_phone_number(phone_number)
        
        if not is_valid:
            return {
                "status": "error",
                "message": f"Invalid phone number: {result}"
            }
        
        formatted_number = result
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if number already exists
        cursor.execute("SELECT id FROM phone_numbers WHERE number = ?", (formatted_number,))
        if cursor.fetchone():
            return {
                "status": "error",
                "message": "Phone number already exists"
            }
        
        # Insert the number
        cursor.execute(
            "INSERT INTO phone_numbers (number) VALUES (?)",
            (formatted_number,)
        )
        conn.commit()
        
        logger.info(f"Added phone number: {formatted_number}")
        
        return {
            "status": "success",
            "message": "Phone number added successfully",
            "number": formatted_number
        }
        
    except Exception as e:
        logger.error(f"Error adding phone number: {e}")
        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }

def get_all_phone_numbers() -> List[Dict]:
    """Get all phone numbers from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, number, added_at 
            FROM phone_numbers 
            WHERE is_active = 1 
            ORDER BY added_at DESC
        """)
        
        rows = cursor.fetchall()
        
        numbers = []
        for row in rows:
            numbers.append({
                "id": row["id"],
                "number": row["number"],
                "added_at": row["added_at"]
            })
        
        return numbers
        
    except Exception as e:
        logger.error(f"Error retrieving phone numbers: {e}")
        return []

def get_phone_number_count() -> int:
    """Get count of active phone numbers"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM phone_numbers WHERE is_active = 1")
        result = cursor.fetchone()
        
        return result["count"] if result else 0
        
    except Exception as e:
        logger.error(f"Error getting phone number count: {e}")
        return 0

def remove_phone_number(phone_number: str) -> Tuple[bool, str]:
    """Remove a phone number from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM phone_numbers WHERE number = ?", (phone_number,))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Removed phone number: {phone_number}")
            return True, "Phone number removed successfully"
        else:
            return False, "Phone number not found"
        
    except Exception as e:
        logger.error(f"Error removing phone number: {e}")
        return False, f"Database error: {str(e)}"

def clear_all_phone_numbers() -> Tuple[bool, str]:
    """Clear all phone numbers from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM phone_numbers")
        count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Cleared {count} phone numbers")
        return True, f"Cleared {count} phone numbers"
        
    except Exception as e:
        logger.error(f"Error clearing phone numbers: {e}")
        return False, f"Database error: {str(e)}"

def log_call_attempt(phone_number: str, call_sid: str = None, status: str = "initiated") -> bool:
    """Log a call attempt"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO call_logs (phone_number, call_sid, status) 
            VALUES (?, ?, ?)
        """, (phone_number, call_sid, status))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error logging call attempt: {e}")
        return False

def get_call_logs(limit: int = 50) -> List[Dict]:
    """Get call logs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT phone_number, call_sid, status, duration, error_message, created_at
            FROM call_logs 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "phone_number": row["phone_number"],
                "call_sid": row["call_sid"],
                "status": row["status"],
                "duration": row["duration"],
                "error_message": row["error_message"],
                "created_at": row["created_at"]
            })
        
        return logs
        
    except Exception as e:
        logger.error(f"Error retrieving call logs: {e}")
        return []

def clear_call_logs() -> Tuple[bool, str]:
    """Clear all call logs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM call_logs")
        count = cursor.rowcount
        conn.commit()
        
        logger.info(f"Cleared {count} call logs")
        return True, f"Cleared {count} call logs"
        
    except Exception as e:
        logger.error(f"Error clearing call logs: {e}")
        return False, f"Database error: {str(e)}"