#!/usr/bin/env python3
"""
Quick setup script for Autodialer Application
"""

import os
import sys
import subprocess
import shutil

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🚀 AUTODIALER APPLICATION SETUP")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    else:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_environment():
    """Setup environment variables"""
    print("\n⚙️ Setting up environment...")
    
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
            print("📝 Please edit .env file with your API credentials")
        else:
            print("❌ .env.example file not found")
    else:
        print("✅ .env file already exists")

def check_api_keys():
    """Check if API keys are configured"""
    print("\n🔑 Checking API configuration...")
    
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            content = f.read()
            
        required_keys = [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN", 
            "TWILIO_PHONE_NUMBER",
            "GEMINI_API_KEY"
        ]
        
        missing_keys = []
        for key in required_keys:
            if f"{key}=" not in content or f"{key}=your-" in content or f"{key}=ACxxxxxxx" in content:
                missing_keys.append(key)
        
        if missing_keys:
            print("⚠️  Please configure these API keys in .env:")
            for key in missing_keys:
                print(f"   - {key}")
        else:
            print("✅ All API keys appear to be configured")
    else:
        print("❌ .env file not found")

def print_next_steps():
    """Print next steps"""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("📋 Next Steps:")
    print("1. Configure your API keys in .env file")
    print("2. Run the application:")
    print("   python run_dev.py")
    print()
    print("3. Open your browser:")
    print("   http://localhost:5000")
    print()
    print("📖 For deployment instructions:")
    print("   See VERCEL_DEPLOYMENT_GUIDE.md")
    print()

def main():
    """Main setup function"""
    print_banner()
    check_python_version()
    install_dependencies()
    setup_environment()
    check_api_keys()
    print_next_steps()

if __name__ == "__main__":
    main()