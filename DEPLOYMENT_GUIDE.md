# 🚀 Fantasy News Center - Permanent Deployment Guide

This guide will help you deploy the Fantasy News Center webhook API to truly permanent cloud infrastructure.

---

## 📦 **Deployment Package Contents**

- `fantasy_webhook_production.py` - Main API application
- `fantasy_news_center_workflow.py` - Core workflow functions
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `railway.toml` - Railway deployment config
- `render.yaml` - Render deployment config
- `Procfile` - Heroku deployment config
- `.env.example` - Environment variables template

---

## 🎯 **Recommended Platform: Railway (Easiest)**

### **Step 1: Create Railway Account**
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended)
3. Verify your account

### **Step 2: Deploy from GitHub**
1. **Upload this deployment folder to a GitHub repository**
2. **Connect Railway to your GitHub account**
3. **Create new project** → **Deploy from GitHub repo**
4. **Select your repository** with the deployment files

### **Step 3: Configure Environment Variables**
In Railway dashboard, add these environment variables:
```
GITHUB_TOKEN=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
PORT=5000
PYTHONUNBUFFERED=1
```

### **Step 4: Deploy**
- Railway will automatically build and deploy
- You'll get a permanent URL like: `https://your-app.railway.app`
- **Cost:** ~$5/month

---

## 🔧 **Alternative: Render (Also Easy)**

### **Step 1: Create Render Account**
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Verify your account

### **Step 2: Create Web Service**
1. **New** → **Web Service**
2. **Connect GitHub repository** with deployment files
3. **Configure:**
   - **Name:** fantasy-news-center-api
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python fantasy_webhook_production.py`

### **Step 3: Environment Variables**
Add in Render dashboard:
```
GITHUB_TOKEN=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
PORT=5000
PYTHONUNBUFFERED=1
```

### **Step 4: Deploy**
- Render builds and deploys automatically
- Get permanent URL like: `https://your-app.onrender.com`
- **Cost:** ~$7/month

---

## 🐳 **Docker Deployment (VPS/Cloud)**

### **For DigitalOcean, Linode, AWS, etc.**

1. **Upload files to your server**
2. **Build Docker image:**
   ```bash
   docker build -t fantasy-news-center .
   ```

3. **Run container:**
   ```bash
   docker run -d \
     --name fantasy-api \
     -p 5000:5000 \
     -e GITHUB_TOKEN=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 \
     -e PORT=5000 \
     --restart unless-stopped \
     fantasy-news-center
   ```

4. **Set up reverse proxy (nginx)** for domain/SSL

---

## 🔥 **Heroku Deployment**

### **Step 1: Install Heroku CLI**
Download from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)

### **Step 2: Deploy**
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-fantasy-api

# Set environment variables
heroku config:set GITHUB_TOKEN=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

# Deploy
git init
git add .
git commit -m "Initial deployment"
git push heroku main
```

**Cost:** ~$7/month

---

## ⚡ **Quick Start (Railway - Recommended)**

### **5-Minute Deployment:**

1. **Create GitHub repo** with these deployment files
2. **Go to railway.app** → Sign up with GitHub
3. **New Project** → **Deploy from GitHub repo**
4. **Add environment variable:** `GITHUB_TOKEN=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`
5. **Deploy** → Get permanent URL

### **Result:**
- ✅ **24/7 uptime** - Never sleeps
- ✅ **Permanent URL** - Never changes
- ✅ **Auto-scaling** - Handles traffic spikes
- ✅ **SSL certificate** - HTTPS included
- ✅ **Monitoring** - Built-in health checks

---

## 🧪 **Testing Your Deployment**

### **Health Check:**
```bash
curl https://your-permanent-url.com/health
```

### **Generate Report:**
```bash
curl -X POST https://your-permanent-url.com/generate-report \
  -H "Content-Type: application/json" \
  -d '{"league_id": "1235357902219247616", "week": 3, "push_to_github": true}'
```

---

## 🔄 **Update Your N8N Integration**

Once deployed, update your N8N HTTP Request node:

**Old URL (temporary):**
```
https://5000-ibali29zm6hilacz1gfud-221e6314.manusvm.computer/generate-report
```

**New URL (permanent):**
```
https://your-app.railway.app/generate-report
```

---

## 💰 **Cost Comparison**

| Platform | Monthly Cost | Ease of Use | Features |
|----------|-------------|-------------|----------|
| **Railway** | ~$5 | ⭐⭐⭐⭐⭐ | Auto-deploy, monitoring |
| **Render** | ~$7 | ⭐⭐⭐⭐⭐ | Free SSL, auto-deploy |
| **Heroku** | ~$7 | ⭐⭐⭐⭐ | Mature platform |
| **DigitalOcean** | ~$5 | ⭐⭐⭐ | Full control, VPS |

---

## 🎯 **Recommendation**

**Use Railway** for the easiest permanent deployment:
1. **Fastest setup** (5 minutes)
2. **Lowest cost** ($5/month)
3. **Best developer experience**
4. **Automatic HTTPS**
5. **Built-in monitoring**

**Your Fantasy News Center will be permanently available 24/7 with a stable URL that never changes!**
