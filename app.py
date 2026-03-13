import os
import json
import random
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import cv2
from fer import FER
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Production configuration
IS_PRODUCTION = bool(os.getenv('RAILWAY_ENVIRONMENT_NAME') or os.getenv('RAILWAY_ENVIRONMENT'))

app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Spotify Configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
SPOTIFY_SCOPE = 'user-read-private user-read-email user-library-read user-top-read user-read-recently-played user-read-playback-state user-modify-playback-state'

# Global detector
detector = FER(mtcnn=True)

# Emotion smoothing buffer per session
emotion_buffers = {}

# Mood to audio feature mapping
MOOD_PROFILES = {
    'happy': {
        'energy': (0.6, 1.0),
        'valence': (0.6, 1.0),
        'tempo': (100, 180),
        'danceability': (0.5, 1.0)
    },
    'sad': {
        'energy': (0.0, 0.4),
        'valence': (0.0, 0.4),
        'tempo': (60, 90),
        'danceability': (0.0, 0.5)
    },
    'calm': {
        'energy': (0.3, 0.5),
        'valence': (0.4, 0.7),
        'tempo': (60, 100),
        'danceability': (0.3, 0.6)
    },
    'angry': {
        'energy': (0.7, 1.0),
        'valence': (0.0, 0.5),
        'tempo': (120, 180),
        'danceability': (0.4, 0.8)
    },
    'energetic': {
        'energy': (0.75, 1.0),
        'valence': (0.5, 1.0),
        'tempo': (110, 180),
        'danceability': (0.6, 1.0)
    },
    'nostalgic': {
        'energy': (0.3, 0.6),
        'valence': (0.3, 0.7),
        'tempo': (80, 120),
        'acousticness': (0.4, 1.0)
    }
}

# Language genre mapping (kept for potential future use)
LANGUAGE_GENRES = {
    'english': ['pop', 'rock', 'indie', 'alternative', 'hip-hop', 'r-n-b'],
    'hindi': ['bollywood', 'indian', 'hindi'],
    'telugu': ['telugu', 'tollywood'],
    'tamil': ['tamil', 'kollywood'],
    'spanish': ['latin', 'spanish', 'reggaeton', 'salsa']
}

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        show_dialog=True
    )

def get_spotify_client():
    token_info = session.get('token_info')
    if not token_info:
        return None
    
    # Check if token is expired
    now = int(time.time())
    is_expired = token_info.get('expires_at', 0) - now < 60
    
    if is_expired:
        sp_oauth = get_spotify_oauth()
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return None
    
    return spotipy.Spotify(auth=token_info['access_token'])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token_info' not in session:
            # For API calls, return JSON error instead of redirect
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated', 'redirect': '/login'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'token_info' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login')
def login():
    if 'token_info' in session:
        return redirect(url_for('index'))
    sp_oauth = get_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    sp_oauth = get_spotify_oauth()
    code = request.args.get('code')
    
    if not code:
        return jsonify({'error': 'No authorization code'}), 400
    
    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        session.permanent = True
        
        # Initialize user session data
        session['last_played_track'] = None
        session['current_mood'] = None
        session['current_language'] = 'auto'
        
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': f'Authentication failed: {str(e)}'}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/user')
@login_required
def get_user():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        user = sp.current_user()
        return jsonify({
            'name': user.get('display_name', 'User'),
            'email': user.get('email'),
            'image': user['images'][0]['url'] if user.get('images') else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect_camera', methods=['POST'])
@login_required
def detect_camera():
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data'}), 400
        
        # Decode base64 image
        import base64
        image_bytes = base64.b64decode(image_data.split(',')[1])
        
        # Convert to image using cv2
        import numpy as np
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        # Detect emotions
        result = detector.detect_emotions(frame)
        
        if not result or len(result) == 0:
            return jsonify({'error': 'No face detected. Please face the camera directly.'}), 400
        
        emotions = result[0]['emotions']
        
        # Get session ID for buffer
        session_id = session.get('session_id', str(time.time()))
        session['session_id'] = session_id
        
        # Smooth emotions
        if session_id not in emotion_buffers:
            emotion_buffers[session_id] = []
        
        emotion_buffers[session_id].append(emotions)
        if len(emotion_buffers[session_id]) > 10:
            emotion_buffers[session_id].pop(0)
        
        # Average emotions manually (no numpy needed for this)
        smoothed = {}
        for emotion in emotions.keys():
            values = [e[emotion] for e in emotion_buffers[session_id]]
            smoothed[emotion] = sum(values) / len(values)
        
        # Get top 3
        sorted_emotions = sorted(smoothed.items(), key=lambda x: x[1], reverse=True)
        top_emotion = sorted_emotions[0][0]
        confidence = sorted_emotions[0][1]
        
        # Map FER emotions to our mood system
        emotion_mapping = {
            'happy': 'happy',
            'sad': 'sad',
            'angry': 'angry',
            'neutral': 'calm',
            'fear': 'sad',
            'surprise': 'energetic',
            'disgust': 'angry'
        }
        
        mapped_mood = emotion_mapping.get(top_emotion, 'calm')
        session['current_mood'] = mapped_mood
        
        return jsonify({
            'dominant_mood': mapped_mood,
            'confidence': float(confidence),
            'all_emotions': {k: float(v) for k, v in sorted_emotions[:3]}
        })
    
    except Exception as e:
        print(f"Camera detection error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@app.route('/api/detect_text', methods=['POST'])
@login_required
def detect_text():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Try AI-powered detection first
        try:
            from text_mood_detector import TextMoodDetector
            
            # Try providers in order of preference
            ai_provider = None
            if os.getenv('OPENAI_API_KEY'):
                ai_provider = 'openai'
            elif os.getenv('GEMINI_API_KEY'):
                ai_provider = 'gemini'
            elif os.getenv('ANTHROPIC_API_KEY'):
                ai_provider = 'anthropic'
            
            if ai_provider:
                print(f"Using AI provider: {ai_provider}")
                detector = TextMoodDetector(provider=ai_provider)
                result = detector.detect_mood(text)
                
                session['current_mood'] = result['dominant_mood']
                
                return jsonify({
                    'emotions': result['emotions'],
                    'dominant_mood': result['dominant_mood'],
                    'confidence': result['confidence'],
                    'method': f'AI ({ai_provider})'
                })
        except Exception as ai_error:
            print(f"AI detection failed: {ai_error}, falling back to keyword matching")
        
        # Fallback: Simple keyword-based emotion detection
        text_lower = text.lower()
        emotions = {
            'happy': 0.0,
            'sad': 0.0,
            'calm': 0.0,
            'angry': 0.0,
            'energetic': 0.0,
            'nostalgic': 0.0
        }
        
        # Keyword matching
        happy_words = ['happy', 'joy', 'excited', 'great', 'wonderful', 'amazing', 'fantastic', 'love', 'good', 'excellent']
        sad_words = ['sad', 'depressed', 'down', 'unhappy', 'crying', 'tears', 'lonely', 'hurt', 'pain', 'miss']
        angry_words = ['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'hate', 'rage', 'pissed']
        calm_words = ['calm', 'peaceful', 'relaxed', 'chill', 'serene', 'tranquil', 'quiet', 'rest']
        energetic_words = ['energetic', 'pumped', 'hyped', 'active', 'excited', 'motivated', 'ready', 'go']
        nostalgic_words = ['nostalgic', 'memories', 'remember', 'past', 'old', 'miss', 'used to', 'back then']
        
        # Count matches
        for word in happy_words:
            if word in text_lower:
                emotions['happy'] += 0.2
        for word in sad_words:
            if word in text_lower:
                emotions['sad'] += 0.2
        for word in angry_words:
            if word in text_lower:
                emotions['angry'] += 0.2
        for word in calm_words:
            if word in text_lower:
                emotions['calm'] += 0.2
        for word in energetic_words:
            if word in text_lower:
                emotions['energetic'] += 0.2
        for word in nostalgic_words:
            if word in text_lower:
                emotions['nostalgic'] += 0.2
        
        # Normalize
        total = sum(emotions.values())
        if total > 0:
            for key in emotions:
                emotions[key] = emotions[key] / total
        else:
            emotions['calm'] = 1.0
        
        # Get dominant emotion
        dominant = max(emotions.items(), key=lambda x: x[1])
        session['current_mood'] = dominant[0]
        
        return jsonify({
            'emotions': emotions,
            'dominant_mood': dominant[0],
            'confidence': dominant[1],
            'method': 'keyword matching (fallback)'
        })
    
    except Exception as e:
        print(f"Text detection error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_mood', methods=['POST'])
@login_required
def set_mood():
    data = request.get_json()
    mood = data.get('mood')
    
    if mood not in MOOD_PROFILES:
        return jsonify({'error': 'Invalid mood'}), 400
    
    session['current_mood'] = mood
    return jsonify({'success': True, 'mood': mood})

@app.route('/api/set_language', methods=['POST'])
@login_required
def set_language():
    # Language feature removed for simplicity
    return jsonify({'success': True})

@app.route('/api/search_song', methods=['POST'])
@login_required
def search_song():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No search query'}), 400
        
        results = sp.search(q=query, type='track', limit=10)
        tracks = results['tracks']['items']
        
        if not tracks:
            return jsonify({'error': 'No tracks found'}), 404
        
        # Return top result
        track = tracks[0]
        return jsonify({
            'track_uri': track['uri'],
            'track_id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/play', methods=['POST'])
@login_required
def play_music():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        data = request.get_json()
        mode = data.get('mode', 'mood')  # mood, search
        
        if mode == 'search':
            track_uri = data.get('track_uri')
            if not track_uri:
                return jsonify({'error': 'No track URI provided'}), 400
            
            # Play specific track
            devices = sp.devices()
            device_list = devices.get('devices', [])
            
            if not device_list:
                return jsonify({'error': 'No active Spotify device found. Please open Spotify on any device.'}), 400
            
            device_id = device_list[0]['id']
            sp.start_playback(device_id=device_id, uris=[track_uri])
            session['last_played_track'] = track_uri
            
            return jsonify({'success': True, 'mode': 'search'})
        
        else:
            # Mood-based playback
            mood = session.get('current_mood')
            
            if not mood:
                return jsonify({'error': 'No mood detected'}), 400
            
            print(f"Playing music for mood: {mood}")
            
            # Get user's music library
            user_tracks = get_user_tracks(sp)
            print(f"Found {len(user_tracks)} user tracks")
            
            if not user_tracks or len(user_tracks) == 0:
                # Fallback: Use Spotify recommendations directly
                print("No user tracks found, using Spotify recommendations")
                try:
                    # Map mood to Spotify recommendation parameters
                    mood_params = {
                        'happy': {'target_valence': 0.8, 'target_energy': 0.7, 'target_danceability': 0.7, 'min_tempo': 100, 'max_tempo': 180},
                        'sad': {'target_valence': 0.2, 'target_energy': 0.3, 'target_danceability': 0.3, 'min_tempo': 60, 'max_tempo': 90},
                        'calm': {'target_valence': 0.5, 'target_energy': 0.4, 'target_danceability': 0.4, 'min_tempo': 60, 'max_tempo': 100},
                        'angry': {'target_valence': 0.3, 'target_energy': 0.85, 'target_danceability': 0.6, 'min_tempo': 120, 'max_tempo': 180},
                        'energetic': {'target_valence': 0.7, 'target_energy': 0.9, 'target_danceability': 0.8, 'min_tempo': 110, 'max_tempo': 180},
                        'nostalgic': {'target_valence': 0.5, 'target_energy': 0.45, 'target_danceability': 0.5, 'min_tempo': 80, 'max_tempo': 120}
                    }
                    params = mood_params.get(mood, mood_params['happy'])
                    recommendations = sp.recommendations(
                        seed_genres=['pop', 'rock', 'indie'],
                        limit=20,
                        target_valence=params["target_valence"],
                        target_energy=params["target_energy"],
                        target_danceability=params.get("target_danceability", 0.5),
                        min_tempo=params.get("min_tempo", 80),
                        max_tempo=params.get("max_tempo", 140)
                    )
                    
                    if recommendations and recommendations.get('tracks'):
                        track = random.choice(recommendations['tracks'])
                        devices = sp.devices()
                        device_list = devices.get('devices', [])
                        
                        if not device_list:
                            return jsonify({'error': 'No active Spotify device found. Please open Spotify on any device.'}), 400
                        
                        device_id = device_list[0]['id']
                        sp.start_playback(device_id=device_id, uris=[track['uri']])
                        session['last_played_track'] = track['uri']
                        
                        return jsonify({
                            'success': True,
                            'mode': 'mood',
                            'mood': mood,
                            'track': {
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'album': track['album']['name'],
                                'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                            }
                        })
                except Exception as e:
                    print(f"Recommendation fallback error: {e}")
                    return jsonify({'error': 'Could not find matching tracks. Please like some songs on Spotify first.'}), 404
            
            # Get audio features for mood matching
            track_ids = [t['id'] for t in user_tracks]
            features = []
            
            # Process in batches of 50
            batch_size = 50
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i:i + batch_size]
                try:
                    batch_features = sp.audio_features(batch)
                    if batch_features:
                        # Filter out None values
                        features.extend([f for f in batch_features if f is not None])
                except Exception as e:
                    print(f"Error getting audio features for batch: {e}")
                    continue
            
            if not features or len(features) == 0:
                # Audio features failed, just play a random track from user library
                print("Audio features failed, playing random track from library")
                selected = random.choice(user_tracks)
                
                devices = sp.devices()
                device_list = devices.get('devices', [])
                
                if not device_list:
                    return jsonify({'error': 'No active Spotify device found. Please open Spotify on any device.'}), 400
                
                device_id = device_list[0]['id']
                sp.start_playback(device_id=device_id, uris=[selected['uri']])
                session['last_played_track'] = selected['uri']
                
                return jsonify({
                    'success': True,
                    'mode': 'mood',
                    'mood': mood,
                    'track': {
                        'name': selected['name'],
                        'artist': selected['artist'],
                        'album': selected['album'],
                        'image': selected['image']
                    }
                })
            
            # Score tracks
            scored_tracks = score_tracks_by_mood(user_tracks, features, mood)
            
            if not scored_tracks or len(scored_tracks) == 0:
                print("No tracks matched mood criteria, playing random track")
                selected = random.choice(user_tracks)
                
                devices = sp.devices()
                device_list = devices.get('devices', [])
                
                if not device_list:
                    return jsonify({'error': 'No active Spotify device found. Please open Spotify on any device.'}), 400
                
                device_id = device_list[0]['id']
                sp.start_playback(device_id=device_id, uris=[selected['uri']])
                session['last_played_track'] = selected['uri']
                
                return jsonify({
                    'success': True,
                    'mode': 'mood',
                    'mood': mood,
                    'track': {
                        'name': selected['name'],
                        'artist': selected['artist'],
                        'album': selected['album'],
                        'image': selected['image']
                    }
                })
            
            # Select from top 10, avoid last played
            last_played = session.get('last_played_track')
            candidates = [t for t in scored_tracks[:min(10, len(scored_tracks))] if t['uri'] != last_played]
            
            if not candidates:
                candidates = scored_tracks[:min(10, len(scored_tracks))]
            
            selected = random.choice(candidates)
            print(f"Selected: {selected['name']} by {selected['artist']} (score: {selected.get('score', 'N/A')})")
            
            # Play track
            devices = sp.devices()
            device_list = devices.get('devices', [])
            
            if not device_list:
                return jsonify({'error': 'No active Spotify device found. Please open Spotify on any device.'}), 400
            
            device_id = device_list[0]['id']
            sp.start_playback(device_id=device_id, uris=[selected['uri']])
            session['last_played_track'] = selected['uri']
            
            return jsonify({
                'success': True,
                'mode': 'mood',
                'mood': mood,
                'track': {
                    'name': selected['name'],
                    'artist': selected['artist'],
                    'album': selected['album'],
                    'image': selected['image']
                }
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/current_track')
@login_required
def current_track():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        current = sp.current_playback()
        
        if not current or not current.get('item'):
            return jsonify({'playing': False})
        
        track = current['item']
        
        return jsonify({
            'playing': True,
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'progress_ms': current['progress_ms'],
            'duration_ms': track['duration_ms'],
            'is_playing': current['is_playing']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices')
@login_required
def get_devices():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        devices = sp.devices()
        device_list = devices.get('devices', [])
        
        return jsonify({
            'devices': [
                {
                    'id': d['id'],
                    'name': d['name'],
                    'type': d['type'],
                    'is_active': d['is_active']
                }
                for d in device_list
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_user_tracks(sp):
    tracks = []
    
    try:
        # Get liked songs
        liked = sp.current_user_saved_tracks(limit=50)
        for item in liked['items']:
            track = item['track']
            if track and track.get('id'):
                tracks.append({
                    'id': track['id'],
                    'uri': track['uri'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                })
        
        # Get top tracks
        top = sp.current_user_top_tracks(limit=50, time_range='short_term')
        for track in top['items']:
            if track and track.get('id') and track['id'] not in [t['id'] for t in tracks]:
                tracks.append({
                    'id': track['id'],
                    'uri': track['uri'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                })
        
        # Get recently played
        recent = sp.current_user_recently_played(limit=50)
        for item in recent['items']:
            track = item['track']
            if track and track.get('id') and track['id'] not in [t['id'] for t in tracks]:
                tracks.append({
                    'id': track['id'],
                    'uri': track['uri'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                })
    
    except Exception as e:
        print(f"Error fetching user tracks: {e}")
    
    return tracks[:100]  # Limit to 100 tracks max

def score_tracks_by_mood(tracks, features, mood):
    if mood not in MOOD_PROFILES:
        return tracks
    
    profile = MOOD_PROFILES[mood]
    scored = []
    
    # Create a map of track_id to feature for faster lookup
    feature_map = {f['id']: f for f in features if f and f.get('id')}
    
    for track in tracks:
        if track['id'] not in feature_map:
            continue
        
        feature = feature_map[track['id']]
        
        try:
            score = 0
            
            # Energy difference
            if 'energy' in profile:
                target_min, target_max = profile['energy']
                target_mid = (target_min + target_max) / 2
                if target_min <= feature['energy'] <= target_max:
                    score += 0  # Perfect match
                else:
                    score += abs(feature['energy'] - target_mid)
            
            # Valence difference
            if 'valence' in profile:
                target_min, target_max = profile['valence']
                target_mid = (target_min + target_max) / 2
                if target_min <= feature['valence'] <= target_max:
                    score += 0  # Perfect match
                else:
                    score += abs(feature['valence'] - target_mid)
            
            # Tempo difference (normalized)
            if 'tempo' in profile:
                target_min, target_max = profile['tempo']
                target_mid = (target_min + target_max) / 2
                if target_min <= feature['tempo'] <= target_max:
                    score += 0  # Perfect match
                else:
                    tempo_diff = abs(feature['tempo'] - target_mid)
                    score += tempo_diff / 100.0  # Normalize
            
            # Danceability
            if 'danceability' in profile:
                target_min, target_max = profile['danceability']
                target_mid = (target_min + target_max) / 2
                if target_min <= feature['danceability'] <= target_max:
                    score += 0  # Perfect match
                else:
                    score += abs(feature['danceability'] - target_mid)
            
            # Acousticness (for nostalgic)
            if 'acousticness' in profile:
                target_min, target_max = profile['acousticness']
                target_mid = (target_min + target_max) / 2
                if target_min <= feature['acousticness'] <= target_max:
                    score += 0  # Perfect match
                else:
                    score += abs(feature['acousticness'] - target_mid)
            
            scored.append({
                **track,
                'score': score,
                'energy': feature['energy'],
                'valence': feature['valence'],
                'tempo': feature['tempo']
            })
        except Exception as e:
            print(f"Error scoring track {track.get('name', 'unknown')}: {e}")
            continue
    
    # Sort by score (lower is better)
    scored.sort(key=lambda x: x['score'])
    
    print(f"Scored {len(scored)} tracks for mood '{mood}'")
    if scored:
        print(f"Best match: {scored[0]['name']} by {scored[0]['artist']} (score: {scored[0]['score']:.2f})")
    
    return scored

@app.route('/api/playback/play-pause', methods=['POST'])
@login_required
def play_pause():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        # Get current playback state
        playback = sp.current_playback()
        
        if not playback:
            return jsonify({'error': 'No active playback'}), 400
        
        is_playing = playback.get('is_playing', False)
        
        if is_playing:
            sp.pause_playback()
            time.sleep(0.3)  # Small delay for Spotify to process
            return jsonify({'success': True, 'is_playing': False})
        else:
            sp.start_playback()
            time.sleep(0.3)  # Small delay for Spotify to process
            return jsonify({'success': True, 'is_playing': True})
    
    except Exception as e:
        print(f"Play/Pause error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playback/next', methods=['POST'])
@login_required
def next_track():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        # Get current playback to ensure we have an active session
        playback = sp.current_playback()
        if not playback:
            return jsonify({'error': 'No active playback'}), 400
        
        sp.next_track()
        time.sleep(0.5)  # Wait for Spotify to skip
        return jsonify({'success': True})
    except Exception as e:
        print(f"Next track error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playback/previous', methods=['POST'])
@login_required
def previous_track():
    sp = get_spotify_client()
    if not sp:
        return jsonify({'error': 'Spotify client unavailable'}), 401
    
    try:
        # Get current playback to ensure we have an active session
        playback = sp.current_playback()
        if not playback:
            return jsonify({'error': 'No active playback'}), 400
        
        # Check current progress - if more than 3 seconds, restart current track
        # Otherwise go to actual previous track
        progress_ms = playback.get('progress_ms', 0)
        
        if progress_ms > 3000:
            # Restart current track by seeking to beginning
            sp.seek_track(0)
        else:
            # Go to previous track
            sp.previous_track()
        
        time.sleep(0.5)  # Wait for Spotify to process
        return jsonify({'success': True})
    except Exception as e:
        print(f"Previous track error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = not IS_PRODUCTION
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
