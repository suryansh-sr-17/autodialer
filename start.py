#!/usr/bin/env python3
"""
Production startup script for Autodialer Application
"""

import os
import sys
from app import app
from config import Config

def main():
    """Start the application in production mode"""
    
    print("🚀 Starting Autodialer Application")
    
    # Check if running in production mode
    if Config.TEST_MODE:
        print("⚠️  WARNING: Running in TEST MODE - only 1800 numbers allowed")
    else:
        print("📱 Production Mode: All valid numbers allowed")
    
    # Check required environment variables
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE_NUMBER',
        'GEMINI_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration")
        sys.exit(1)
    
    print("✅ All required environment variables are set")
    print(f"📊 Access the application at: http://localhost:5000")
    print(f"📋 API Documentation: http://localhost:5000/health")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start the Flask application
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=False
    )

if __name__ == '__main__':
    main()