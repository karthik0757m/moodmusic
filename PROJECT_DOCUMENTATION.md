# 🎵 Mood Music Player - Complete Documentation

## Project Overview
AI-powered mood-based music player that detects emotions and plays matching Spotify tracks.

## Features
- 📷 Camera-based emotion detection (FER + MTCNN)
- 💭 Text-based mood analysis (AI-powered with Gemini)
- 🎚 Manual mood selection
- 🔍 Direct song search
- 🎵 Auto-play with personalized recommendations
- 🎮 Playback controls (play/pause, next, previous)

## Tech Stack
- **Backend**: Flask 3.1.0, Python 3.10
- **AI/ML**: FER 22.4.0, OpenCV, Google Gemini
- **Music**: Spotify Web API (Spotipy 2.25.0)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

## Quick Start

### Prerequisites
- Python 3.10+
- Spotify Premium account
- Spotify Developer App credentials
- Google Gemini API key

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables in .env
FLASK_SECRET_KEY=your-secret-key
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
GEMINI_API_KEY=your-gemini-key

# Run locally
python app.py
```

### Spotify Setup
1. Go to https://developer.spotify.com/dashboard
2. Create new app
3. Add redirect URI: `http://127.0.0.1:5000/callback`
4. Copy Client ID and Secret to .env

## Architecture

### Multi-User OAuth Flow
- Session-based authentication
- Automatic token refresh
- Secure credential management

### Mood Detection Modes
1. **Camera**: Real-time facial emotion recognition
2. **Text**: AI-powered sentiment analysis with Gemini
3. **Manual**: Direct mood selection (6 moods)
4. **Search**: Direct song search and play

### Recommendation Engine
Uses Spotify audio features for intelligent matching:
- **Valence**: Musical positivity (0.0 - 1.0)
- **Energy**: Intensity and activity (0.0 - 1.0)
- **Tempo**: BPM (beats per minute)
- **Danceability**: Rhythm suitability (0.0 - 1.0)

### Mood Profiles
```python
happy: high energy, high valence, fast tempo
sad: low energy, low valence, slow tempo
calm: moderate energy, moderate valence, slow tempo
angry: high energy, low valence, fast tempo
energetic: very high energy, high valence, fast tempo
nostalgic: moderate energy, moderate valence, moderate tempo
```

## API Endpoints

### Authentication
- `GET /login` - Initiate Spotify OAuth
- `GET /callback` - OAuth callback handler
- `GET /logout` - Clear session

### Mood Detection
- `POST /api/detect_camera` - Analyze camera image
- `POST /api/detect_text` - Analyze text input
- `POST /api/set_mood` - Set mood manually

### Music Control
- `POST /api/play` - Play music based on mood
- `POST /api/search_song` - Search for specific song
- `GET /api/current_track` - Get now playing info
- `POST /api/playback/play-pause` - Toggle playback
- `POST /api/playback/next` - Skip to next track
- `POST /api/playback/previous` - Previous track

### User Info
- `GET /api/user` - Get current user info
- `GET /api/devices` - Get available Spotify devices

## Deployment

### Railway (Recommended)
1. Push code to GitHub
2. Connect Railway to repository
3. Add environment variables
4. Update Spotify redirect URI to Railway URL
5. Deploy automatically

### Environment Variables for Production
```
FLASK_SECRET_KEY=random-secret-key
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
SPOTIFY_REDIRECT_URI=https://your-app.railway.app/callback
GEMINI_API_KEY=your-gemini-key
```

## Troubleshooting

### No Spotify device found
- Open Spotify app on any device
- Play any song once to activate device

### Camera not working
- Allow camera permissions in browser
- Check if camera is being used by another app

### Token refresh fails
- Logout and login again
- Check Spotify credentials in .env

### No tracks found
- Like some songs on Spotify first
- Check if Spotify account has listening history

## Project Structure
```
mood-music-player/
├── app.py                 # Main Flask application
├── text_mood_detector.py  # AI text analysis
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── templates/
│   ├── index.html        # Main UI
│   └── login.html        # Login page
└── static/
    ├── css/
    │   └── style.css     # Styling
    └── js/
        └── app.js        # Frontend logic
```

## Security Notes
- Never commit .env file
- Use HTTPS in production
- Rotate API keys regularly
- Enable secure cookies in production

## License
MIT License - Free to use for learning and personal projects
