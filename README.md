# 🎵 Mood Music Player

AI-powered music player that detects your emotions and plays matching Spotify tracks.

## ✨ Features

- 📷 **Camera Detection** - Real-time facial emotion recognition
- 💭 **Text Analysis** - AI-powered mood detection with Google Gemini
- 🎚 **Manual Selection** - Choose from 6 moods directly
- 🔍 **Song Search** - Search and play any Spotify track
- 🎵 **Smart Recommendations** - Personalized music based on audio features
- 🎮 **Playback Controls** - Play, pause, next, previous

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` file:
```env
FLASK_SECRET_KEY=your-random-secret-key
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Setup Spotify App
1. Go to https://developer.spotify.com/dashboard
2. Create new app
3. Add redirect URI: `http://127.0.0.1:5000/callback`
4. Copy credentials to `.env`

### 4. Run Locally
```bash
python app.py
```
Open http://localhost:5000

## 🚂 Deploy to Railway

See [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for complete deployment guide.

Quick steps:
1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables
4. Update Spotify redirect URI
5. Deploy!

## 📚 Documentation

- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) - Complete technical documentation
- [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) - Deployment guide

## 🛠️ Tech Stack

- **Backend**: Flask, Python 3.10
- **AI/ML**: FER, OpenCV, Google Gemini
- **Music**: Spotify Web API
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

## 📝 License

MIT License
