# Autodialer Application

A simple Python-based MVP system that enables automated phone calling to multiple Indian phone numbers using Twilio's API.

## Features

- Bulk calling to multiple phone numbers
- AI prompt commands powered by Google Gemini for natural language operation
- Call logging and statistics
- Minimal web interface
- Test mode for development

## Prerequisites

- Python 3.7+
- Twilio Account (for making calls)
- Google Gemini API Key (for AI command processing)

## Setup Instructions

### Getting API Keys

1. **Twilio Setup**
   - Sign up at [Twilio Console](https://console.twilio.com/)
   - Get your Account SID, Auth Token, and purchase a phone number
   
2. **Gemini API Setup**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key for Gemini
   - Copy the API key for configuration

### Local Development

1. **Clone and navigate to the project directory**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Fill in your Twilio credentials and Gemini API key:
     ```
     TWILIO_ACCOUNT_SID=your-twilio-account-sid
     TWILIO_AUTH_TOKEN=your-twilio-auth-token
     TWILIO_PHONE_NUMBER=your-twilio-phone-number
     GEMINI_API_KEY=your-gemini-api-key
     ```

4. **Initialize the database**
   The database will be automatically initialized when you first run the application.

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to `http://localhost:5000`

### Vercel Deployment

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Deploy to Vercel**
   ```bash
   vercel
   ```

3. **Set environment variables in Vercel dashboard**
   - Add your Twilio credentials
   - Set `TEST_MODE=False` for production

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token | Yes |
| `TWILIO_PHONE_NUMBER` | Your Twilio Phone Number | Yes |
| `GEMINI_API_KEY` | Your Google Gemini API Key | Yes |
| `SECRET_KEY` | Flask secret key | No (auto-generated) |
| `TEST_MODE` | Enable test mode (1800 numbers only) | No (default: True) |
| `MAX_NUMBERS` | Maximum numbers to process | No (default: 100) |

## Test Mode

When `TEST_MODE=True`, the application only accepts phone numbers in the format `1800 XXXX XXXX` to prevent accidental calls to real numbers during development.

## Project Structure

```
autodialer/
├── app.py                 # Main Flask application
├── config.py              # Configuration management
├── models.py              # Database models and operations
├── ai_processor.py        # AI command processing
├── gemini_processor.py    # Google Gemini integration
├── call_manager.py        # Twilio call management
├── command_handlers.py    # Command processing logic
├── number_handler.py      # Phone number validation
├── number_importer.py     # Bulk number import
├── error_handler.py       # Error handling utilities
├── logging_config.py      # Logging configuration
├── run_dev.py            # Development server
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment configuration
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── API_DOCUMENTATION.md  # API documentation
├── static/
│   ├── css/styles.css    # Web interface styles
│   └── js/app.js         # Frontend JavaScript
├── templates/
│   └── index.html        # Web interface template
└── README.md             # This file
```

## Usage

1. **Add Phone Numbers**: Use the web interface to copy-paste or upload phone numbers
2. **AI Commands**: Use natural language commands like "call all numbers" or "add number +91XXXXXXXXXX"
3. **Start Calling**: Click the "Start Calling" button to begin bulk calling
4. **View Logs**: Monitor call progress and view detailed logs and statistics

## API Endpoints

The application provides REST API endpoints for integration:

- `GET /` - Web interface
- `POST /numbers` - Add a single phone number
- `POST /upload-numbers` - Bulk upload phone numbers
- `GET /get-numbers` - Retrieve all stored numbers
- `POST /start-calling` - Start the calling process
- `GET /call-logs` - Get call logs and statistics
- `POST /ai-command` - Process AI commands
- `GET /health` - Health check endpoint

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.