#!/usr/bin/env python3
"""
Development server runner with auto-reload and debugging
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Set development environment (but don't override existing values)
if not os.getenv('ENVIRONMENT'):
    os.environ['ENVIRONMENT'] = 'development'
if not os.getenv('FLASK_DEBUG'):
    os.environ['FLASK_DEBUG'] = 'True'

if __name__ == '__main__':
    try:
        from app import app
        from logging_config import initialize_logging
        
        # Initialize logging for development
        initialize_logging(log_level='DEBUG', debug_mode=True)
        
        # Check current test mode setting
        test_mode = os.getenv('TEST_MODE', 'True').lower() == 'true'
        
        print("🚀 Starting Autodialer Development Server")
        print(f"📱 Test Mode: {'Only 1800 numbers will be called' if test_mode else 'All valid numbers allowed'}")
        print("🔧 Debug Mode: Enabled")
        print("📊 Access the application at: http://localhost:5000")
        print("📋 API Documentation: http://localhost:5000/health")
        print("\n⚠️  Make sure to configure your .env file with API credentials")
        if not test_mode:
            print("🚨 WARNING: Test mode is DISABLED - real calls will be attempted!")
        print("\nPress Ctrl+C to stop the server\n")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n👋 Development server stopped")
    except Exception as e:
        print(f"❌ Error starting development server: {e}")
        sys.exit(1)