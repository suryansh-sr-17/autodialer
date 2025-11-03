# 🚀 Complete Vercel Deployment Guide

<div align="center">

![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)

**Deploy your Autodialer application to Vercel in minutes!**

</div>

---

## 📋 Prerequisites

Before deploying to Vercel, ensure you have:

- ✅ **GitHub Account** (where your code is hosted)
- ✅ **Vercel Account** (free tier available)
- ✅ **Twilio Account** with credentials
- ✅ **Google Gemini API Key**
- ✅ **Your repository** pushed to GitHub

---

## 🎯 Method 1: One-Click Deployment (Recommended)

### Step 1: Click Deploy Button

Click the deploy button in your repository README:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/suryansh-sr-17/autodialer)

### Step 2: Configure Repository

1. **Sign in** to Vercel (or create account)
2. **Import** your GitHub repository
3. **Configure** project settings:
   - **Project Name**: `autodialer` (or your preferred name)
   - **Framework Preset**: `Other`
   - **Root Directory**: `./` (leave default)

### Step 3: Set Environment Variables

Add these **required** environment variables:

| Variable | Value | Where to Get |
|----------|-------|--------------|
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxx` | [Twilio Console](https://console.twilio.com/) |
| `TWILIO_AUTH_TOKEN` | `your-auth-token` | [Twilio Console](https://console.twilio.com/) |
| `TWILIO_PHONE_NUMBER` | `+1234567890` | [Twilio Console](https://console.twilio.com/) |
| `GEMINI_API_KEY` | `your-gemini-key` | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| `TEST_MODE` | `False` | Set to `False` for production |

### Step 4: Deploy

1. Click **"Deploy"**
2. Wait for build to complete (2-3 minutes)
3. Get your live URL: `https://your-app-name.vercel.app`

---

## 🛠️ Method 2: Vercel CLI Deployment

### Step 1: Install Vercel CLI

```bash
# Install globally
npm install -g vercel

# Or using yarn
yarn global add vercel
```

### Step 2: Login to Vercel

```bash
vercel login
```

Follow the prompts to authenticate with your Vercel account.

### Step 3: Deploy from Terminal

```bash
# Navigate to your project directory
cd autodialer

# Deploy to Vercel
vercel

# Follow the prompts:
# ? Set up and deploy "~/autodialer"? [Y/n] y
# ? Which scope do you want to deploy to? [Your Account]
# ? Link to existing project? [y/N] n
# ? What's your project's name? autodialer
# ? In which directory is your code located? ./
```

### Step 4: Set Environment Variables via CLI

```bash
# Set production environment variables
vercel env add TWILIO_ACCOUNT_SID
# Enter your Twilio Account SID when prompted

vercel env add TWILIO_AUTH_TOKEN
# Enter your Twilio Auth Token when prompted

vercel env add TWILIO_PHONE_NUMBER
# Enter your Twilio Phone Number when prompted

vercel env add GEMINI_API_KEY
# Enter your Gemini API Key when prompted

vercel env add TEST_MODE
# Enter "False" for production
```

### Step 5: Redeploy with Environment Variables

```bash
vercel --prod
```

---

## 🔧 Configuration Details

### Vercel Configuration (`vercel.json`)

Your project includes a pre-configured `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ],
  "env": {
    "FLASK_ENV": "production"
  }
}
```

### Python Runtime

Vercel automatically detects Python version from `runtime.txt` (if present) or uses Python 3.9 by default.

---

## 🔐 Environment Variables Setup Guide

### 🔑 Getting Twilio Credentials

1. **Sign up** at [Twilio Console](https://console.twilio.com/)
2. **Navigate** to Dashboard
3. **Copy** your Account SID and Auth Token
4. **Buy a phone number** from Phone Numbers → Manage → Buy a number
5. **Copy** the purchased phone number

### 🧠 Getting Gemini API Key

1. **Visit** [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Sign in** with your Google account
3. **Click** "Create API Key"
4. **Copy** the generated API key

### ⚙️ Setting Variables in Vercel Dashboard

1. **Go to** [Vercel Dashboard](https://vercel.com/dashboard)
2. **Select** your project
3. **Click** "Settings" tab
4. **Click** "Environment Variables"
5. **Add** each variable:
   - **Name**: Variable name (e.g., `TWILIO_ACCOUNT_SID`)
   - **Value**: Your actual value
   - **Environment**: Select "Production", "Preview", and "Development"

---

## 🚀 Post-Deployment Steps

### 1. Verify Deployment

Visit your Vercel URL and check:
- ✅ **Homepage loads** correctly
- ✅ **No error messages** in browser console
- ✅ **Environment variables** are working

### 2. Test Basic Functionality

1. **Add a test number** (1800 format if TEST_MODE=True)
2. **Try AI commands** in the interface
3. **Check logs** in Vercel dashboard

### 3. Monitor Performance

- **Check** Vercel Analytics
- **Monitor** function execution times
- **Review** error logs in dashboard

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### ❌ Build Fails

**Problem**: Build fails during deployment

**Solutions**:
```bash
# Check Python version compatibility
# Ensure requirements.txt is present
# Verify vercel.json syntax
```

#### ❌ Environment Variables Not Working

**Problem**: App can't access environment variables

**Solutions**:
1. **Verify** variables are set in Vercel dashboard
2. **Check** variable names match exactly
3. **Redeploy** after adding variables

#### ❌ Database Issues

**Problem**: SQLite database not persisting

**Solutions**:
- Vercel is **serverless** - database resets between requests
- Consider using **Vercel Postgres** or **external database**
- For MVP, current SQLite setup works for testing

#### ❌ Function Timeout

**Problem**: Requests timing out

**Solutions**:
```bash
# Optimize code for faster execution
# Consider upgrading Vercel plan for longer timeouts
# Implement async operations where possible
```

### 📊 Vercel Limits (Free Tier)

| Resource | Limit | Impact |
|----------|-------|--------|
| **Function Duration** | 10 seconds | May affect long calls |
| **Bandwidth** | 100GB/month | Sufficient for most use |
| **Deployments** | Unlimited | No restrictions |
| **Team Members** | 3 | Good for small teams |

---

## 🔄 Continuous Deployment

### Automatic Deployments

Vercel automatically deploys when you push to GitHub:

1. **Push** changes to your repository
2. **Vercel** detects changes automatically
3. **New deployment** starts within seconds
4. **Live URL** updates after successful build

### Branch Deployments

- **Main branch** → Production deployment
- **Other branches** → Preview deployments
- **Pull requests** → Automatic preview URLs

---

## 📈 Monitoring and Analytics

### Vercel Dashboard Features

1. **Function Logs**: Real-time execution logs
2. **Analytics**: Traffic and performance metrics
3. **Deployments**: History of all deployments
4. **Domains**: Custom domain management

### Setting Up Monitoring

```bash
# View real-time logs
vercel logs [deployment-url]

# Check function performance
# Visit Vercel Dashboard → Analytics
```

---

## 🎯 Production Checklist

Before going live, ensure:

- [ ] **TEST_MODE=False** in production environment
- [ ] **All environment variables** are set correctly
- [ ] **Twilio account** has sufficient balance
- [ ] **Phone numbers** are validated
- [ ] **Error handling** is working properly
- [ ] **Rate limiting** is considered
- [ ] **Monitoring** is set up

---

## 🆘 Getting Help

### Resources

- 📖 **Vercel Documentation**: [vercel.com/docs](https://vercel.com/docs)
- 💬 **Vercel Community**: [github.com/vercel/vercel/discussions](https://github.com/vercel/vercel/discussions)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/suryansh-sr-17/autodialer/issues)

### Support Channels

1. **Vercel Support**: Available in dashboard
2. **GitHub Issues**: For code-related problems
3. **Community Forums**: For general questions

---

<div align="center">

## 🎉 Congratulations!

Your Autodialer application is now live on Vercel!

**Share your deployment**: `https://your-app-name.vercel.app`

[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com)

</div>