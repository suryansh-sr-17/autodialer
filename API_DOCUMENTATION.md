# Autodialer API Documentation

## Base URL
- Local Development: `http://localhost:5000`
- Production: `https://your-domain.com`

## Authentication
Currently, no authentication is required for API endpoints.

## Core Endpoints

### 1. Main Interface
- **GET** `/` - Main web interface page
- **GET** `/health` - Health check endpoint
- **GET** `/system-status` - Detailed system status

### 2. Phone Number Management
- **GET** `/numbers` - Get all phone numbers
- **POST** `/numbers` - Add a single phone number
- **DELETE** `/numbers/<number>` - Delete a specific phone number  
- **DELETE** `/numbers` - Clear all phone numbers

### 3. AI Command Processing
- **POST** `/ai-command` - Process natural language commands
- **POST** `/upload-numbers` - Process bulk number input (text)
- **POST** `/api/upload-file` - Process file upload for numbers

### 4. Call Management
- **POST** `/start-calling` - Start bulk calling all numbers
- **POST** `/api/call-single` - Make a call to single number
- **GET** `/api/call-status/<call_sid>` - Get status of specific call

### 5. Data & Analytics
- **GET** `/call-logs` - Get call history with filtering
- **GET** `/call-statistics` - Get call statistics and analytics
- **GET** `/api/dashboard-data` - Get comprehensive dashboard data

### 6. Utilities
- **POST** `/api/validate-number` - Validate phone number format

## Request/Response Examples

### Add Phone Number
```http
POST /numbers
Content-Type: application/json

{
    "number": "+919876543210"
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Phone number added successfully",
    "number": "+919876543210"
}
```

### AI Command Processing
```http
POST /ai-command
Content-Type: application/json

{
    "command": "call all numbers"
}
```

**Response:**
```json
{
    "status": "success",
    "parsed_command": {
        "action": "call_all",
        "confidence": 0.95
    },
    "execution_result": {
        "status": "success",
        "statistics": {
            "total": 5,
            "successful": 4,
            "failed": 1
        }
    },
    "response": "Started calling 5 numbers! 4 calls initiated successfully."
}
```

### Bulk Number Upload
```http
POST /upload-numbers
Content-Type: application/json

{
    "numbers": "+919876543210\n+911800123456\n9876543211"
}
```

**Response:**
```json
{
    "status": "success",
    "valid_numbers": ["+919876543210", "+911800123456", "+919876543211"],
    "duplicates": [],
    "invalid_numbers": [],
    "response": "Successfully added 3 phone numbers!"
}
```

### Get Call Statistics
```http
GET /call-statistics?days=7
```

**Response:**
```json
{
    "status": "success",
    "statistics": {
        "total_calls": 25,
        "successful_calls": 20,
        "failed_calls": 5,
        "success_rate": 80.0,
        "avg_duration": 45.5
    }
}
```

### Start Bulk Calling
```http
POST /start-calling
Content-Type: application/json

{
    "message": "Hello, this is a test call",
    "delay": 3
}
```

**Response:**
```json
{
    "status": "completed",
    "statistics": {
        "total": 10,
        "successful": 8,
        "failed": 2,
        "success_rate": 80.0
    },
    "results": [...]
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "status": "error",
    "message": "Descriptive error message",
    "error_code": 400
}
```

## Status Codes
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable (health check failure)

## CORS Support
The API supports CORS for the following origins:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5000`

## Rate Limiting
Currently, no rate limiting is implemented. Consider adding rate limiting for production use.

## File Upload Support
Supported file formats for number upload:
- `.txt` - Plain text files
- `.csv` - Comma-separated values

Files must be UTF-8 encoded and contain phone numbers separated by newlines or commas.