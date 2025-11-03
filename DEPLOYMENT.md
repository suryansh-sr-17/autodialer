# Deployment Guide

## Quick Start

### Local Development
1. **Clone the repository**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Setup environment**: Copy `.env.example` to `.env` and fill in your API keys
4. **Run development server**: `python run_dev.py`
5. **Access application**: http://localhost:5000

### Production Deployment
1. **Setup environment**: Ensure all required environment variables are set
2. **Run production server**: `python start.py`
3. **Or use gunicorn**: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`

## Environment Variables

### Required
- `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token  
- `TWILIO_PHONE_NUMBER` - Your Twilio Phone Number
- `GEMINI_API_KEY` - Your Google Gemini API Key

### Optional
- `TEST_MODE` - Set to `False` for production (default: `True`)
- `MAX_NUMBERS` - Maximum numbers to store (default: `100`)
- `SECRET_KEY` - Flask secret key (auto-generated if not provided)

## Deployment Platforms

### Vercel (Recommended)

**🚀 One-Click Deploy:**
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/suryansh-sr-17/autodialer)

**📖 Detailed Guide:** See [VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md) for complete step-by-step instructions.

**Quick CLI Deploy:**
```bash
npm install -g vercel
vercel
```

### Heroku
```bash
git init
heroku create your-app-name
heroku config:set TWILIO_ACCOUNT_SID=your-sid
heroku config:set TWILIO_AUTH_TOKEN=your-token
heroku config:set TWILIO_PHONE_NUMBER=your-number
heroku config:set GEMINI_API_KEY=your-key
heroku config:set TEST_MODE=False
git add .
git commit -m "Initial deployment"
git push heroku main
```

### Railway
```bash
railway login
railway init
railway add
railway up
```
Set environment variables in Railway dashboard.

## Production Checklist

- [ ] Set `TEST_MODE=False`
- [ ] Configure all required environment variables
- [ ] Test with a small number of calls first
- [ ] Monitor call logs and error rates
- [ ] Set up proper logging and monitoring
- [ ] Configure rate limiting if needed
- [ ] Verify Twilio account has sufficient balance

## Security Notes

- Never commit `.env` file to version control
- Use strong secret keys in production
- Consider implementing rate limiting
- Monitor API usage and costs
- Regularly rotate API keys