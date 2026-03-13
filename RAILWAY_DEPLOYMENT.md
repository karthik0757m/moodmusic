# 🚂 Railway Deployment Guide

## Quick Deploy to Railway

### Step 1: Prepare Your Repository
Your app is now Railway-ready with these files:
- ✅ `requirements.txt` - Updated with gunicorn
- ✅ `Procfile` - Start command
- ✅ `railway.json` - Railway configuration
- ✅ `nixpacks.toml` - Build configuration
- ✅ `.railwayignore` - Files to exclude
- ✅ `runtime.txt` - Python version

### Step 2: Push to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Step 3: Deploy on Railway

1. **Go to Railway**: https://railway.app
2. **Sign up/Login** with GitHub
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your repository**

### Step 4: Configure Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```
FLASK_SECRET_KEY=your-secret-key-here
SPOTIFY_CLIENT_ID=b47b75b2b2264d84a2af0682e9a305d4
SPOTIFY_CLIENT_SECRET=76b6a69f0dc646b3a9017d02bd7f6d38
SPOTIFY_REDIRECT_URI=https://your-app.railway.app/callback
GEMINI_API_KEY=AIzaSyDQDN_527K8Gf3vv0FhaTKl1cIBwUK01iI
```

**Important**: Update `SPOTIFY_REDIRECT_URI` after deployment!

### Step 5: Update Spotify App Settings

1. Go to https://developer.spotify.com/dashboard
2. Select your app
3. Click "Edit Settings"
4. Add your Railway URL to **Redirect URIs**:
   ```
   https://your-app.railway.app/callback
   ```
5. Click "Save"

### Step 6: Deploy!

Railway will automatically:
- ✅ Detect Python
- ✅ Install dependencies
- ✅ Build your app
- ✅ Deploy and provide a URL

