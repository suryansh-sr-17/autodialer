# 📞 Autodialer Application

<div align="center">

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3.3-green.svg)
![Twilio](https://img.shields.io/badge/twilio-API-red.svg)
![Gemini](https://img.shields.io/badge/google-gemini-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**🚀 A powerful AI-driven autodialer system for bulk phone calling with natural language commands**

[🌐 Live Demo](https://autodialer-suryansh.vercel.app) • [📖 Documentation](./API_DOCUMENTATION.md) • [🚀 Deploy](./DEPLOYMENT.md)

</div>

---

## ✨ Features

<table>
<tr>
<td>

🤖 **AI-Powered Commands**
- Natural language processing with Google Gemini
- Smart command interpretation
- Conversational interface

📞 **Bulk Calling System**
- Mass phone number management
- Automated calling sequences
- Real-time call monitoring

</td>
<td>

📊 **Analytics & Logging**
- Comprehensive call statistics
- Detailed error tracking
- Performance metrics

🛡️ **Safety Features**
- Test mode for development
- Number validation
- Rate limiting protection

</td>
</tr>
</table>

## 📸 Screenshots

<div align="center">

### 🖥️ Web Interface
*Clean and intuitive dashboard for managing your autodialer*

![Dashboard](https://via.placeholder.com/800x400/1a1a1a/ffffff?text=🚀+Autodialer+Dashboard+Coming+Soon)

### 🤖 AI Command Interface
*Natural language processing for seamless interaction*

![AI Commands](https://via.placeholder.com/800x300/2d3748/ffffff?text=💬+AI+Commands+Interface)

</div>

## 🛠️ Tech Stack

<div align="center">

| Backend | Frontend | AI/ML | Cloud |
|---------|----------|-------|-------|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white) | ![Google](https://img.shields.io/badge/Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white) | ![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white) |
| ![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white) | ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white) | ![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white) | ![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white) |

</div>

## 📋 Prerequisites

- 🐍 **Python 3.7+**
- 📱 **Twilio Account** (for making calls)
- 🧠 **Google Gemini API Key** (for AI command processing)

## 🚀 Quick Start

### 🔑 Getting API Keys

<details>
<summary><b>🔧 Twilio Setup</b></summary>

1. Sign up at [Twilio Console](https://console.twilio.com/)
2. Get your **Account SID**, **Auth Token**
3. Purchase a phone number
4. Copy credentials for configuration

</details>

<details>
<summary><b>🧠 Gemini API Setup</b></summary>

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key for Gemini
3. Copy the API key for configuration

</details>

### 💻 Local Development

```bash
# 📥 Clone the repository
git clone https://github.com/suryansh-sr-17/autodialer.git
cd autodialer

# 📦 Install dependencies
pip install -r requirements.txt

# ⚙️ Setup environment variables
cp .env.example .env
# Edit .env with your API keys

# 🚀 Run the application
python run_dev.py

# 🌐 Access the application
# Open http://localhost:5000 in your browser
```

### ☁️ One-Click Deployment

<div align="center">

[![Deploy with Vercel](https://vercel.com/button)]([https://vercel.com/new/clone?repository-url=https://github.com/suryansh-sr-17/autodialer](https://autodialer-1.vercel.app/))
</div>

**Manual Deployment:**
```bash
# 📦 Install Vercel CLI
npm install -g vercel

# 🚀 Deploy to Vercel
vercel

# ⚙️ Set environment variables in dashboard
# Add your Twilio credentials and set TEST_MODE=False
```

## 🔐 Environment Variables

<div align="center">

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| 🔑 `TWILIO_ACCOUNT_SID` | Your Twilio Account SID | ✅ Required | - |
| 🔐 `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token | ✅ Required | - |
| 📞 `TWILIO_PHONE_NUMBER` | Your Twilio Phone Number | ✅ Required | - |
| 🧠 `GEMINI_API_KEY` | Your Google Gemini API Key | ✅ Required | - |
| 🔒 `SECRET_KEY` | Flask secret key | ⚪ Optional | Auto-generated |
| 🧪 `TEST_MODE` | Enable test mode (1800 numbers only) | ⚪ Optional | `True` |
| 📊 `MAX_NUMBERS` | Maximum numbers to process | ⚪ Optional | `100` |

</div>

## 🧪 Test Mode

<div align="center">

![Test Mode](https://img.shields.io/badge/Test%20Mode-Enabled-yellow?style=for-the-badge)
![Safety](https://img.shields.io/badge/Safety-First-green?style=for-the-badge)

</div>

When `TEST_MODE=True`, the application only accepts phone numbers in the format `1800 XXXX XXXX` to prevent accidental calls to real numbers during development.

> ⚠️ **Safety First**: Always test with 1800 numbers before switching to production mode!

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

## 📱 Usage

<div align="center">

### 🎯 Simple 4-Step Process

</div>

| Step | Action | Description |
|------|--------|-------------|
| 1️⃣ | **📝 Add Numbers** | Use the web interface to copy-paste or upload phone numbers |
| 2️⃣ | **🤖 AI Commands** | Use natural language: *"call all numbers"* or *"add number +91XXXXXXXXXX"* |
| 3️⃣ | **🚀 Start Calling** | Click the "Start Calling" button to begin bulk calling |
| 4️⃣ | **📊 Monitor** | View real-time logs, statistics, and call progress |

### 💬 AI Command Examples

```
🗣️ "Call all the numbers in my list"
🗣️ "Add the number +919876543210 to my contacts"
🗣️ "Show me the call statistics"
🗣️ "Stop all ongoing calls"
```

## 🔌 API Endpoints

<div align="center">

![API](https://img.shields.io/badge/API-RESTful-blue?style=for-the-badge)
![JSON](https://img.shields.io/badge/Format-JSON-orange?style=for-the-badge)

</div>

| Method | Endpoint | Description | 
|--------|----------|-------------|
| 🌐 `GET` | `/` | Web interface |
| ➕ `POST` | `/numbers` | Add a single phone number |
| 📤 `POST` | `/upload-numbers` | Bulk upload phone numbers |
| 📋 `GET` | `/get-numbers` | Retrieve all stored numbers |
| 🚀 `POST` | `/start-calling` | Start the calling process |
| 📊 `GET` | `/call-logs` | Get call logs and statistics |
| 🤖 `POST` | `/ai-command` | Process AI commands |
| ❤️ `GET` | `/health` | Health check endpoint |

> 📖 **Full API Documentation**: [View detailed API docs](./API_DOCUMENTATION.md)

## 🤝 Contributing

<div align="center">

![Contributors](https://img.shields.io/github/contributors/suryansh-sr-17/autodialer?style=for-the-badge)
![Issues](https://img.shields.io/github/issues/suryansh-sr-17/autodialer?style=for-the-badge)
![Pull Requests](https://img.shields.io/github/issues-pr/suryansh-sr-17/autodialer?style=for-the-badge)

</div>

We welcome contributions! Here's how you can help:

1. 🍴 **Fork** the repository
2. 🌿 **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. 💻 **Make** your changes
4. ✅ **Test** thoroughly
5. 📝 **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. 📤 **Push** to the branch (`git push origin feature/amazing-feature`)
7. 🔄 **Submit** a pull request

### 🐛 Found a Bug?
[Report it here](https://github.com/suryansh-sr-17/autodialer/issues/new?template=bug_report.md)

### 💡 Have an Idea?
[Suggest a feature](https://github.com/suryansh-sr-17/autodialer/issues/new?template=feature_request.md)

---

<div align="center">

## 📄 License

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

### 🌟 Show Your Support

If this project helped you, please consider giving it a ⭐!

[![GitHub stars](https://img.shields.io/github/stars/suryansh-sr-17/autodialer?style=social)](https://github.com/suryansh-sr-17/autodialer/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/suryansh-sr-17/autodialer?style=social)](https://github.com/suryansh-sr-17/autodialer/network/members)

**Made with ❤️ by [Suryansh](https://github.com/suryansh-sr-17)**

</div>
