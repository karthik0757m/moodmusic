// Global state
let currentMode = 'camera';
let videoStream = null;
let currentTrackInterval = null;
let progressAnimationFrame = null;
let trackData = {
    progress_ms: 0,
    duration_ms: 0,
    lastUpdate: 0,
    isPlaying: false
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadUser();
    initCamera();
    startCurrentTrackPolling();
    loadTheme();
});

// Theme Management
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        document.getElementById('theme-toggle').checked = true;
    }
}

function toggleTheme() {
    const isLight = document.getElementById('theme-toggle').checked;
    if (isLight) {
        document.body.classList.add('light-mode');
        localStorage.setItem('theme', 'light');
    } else {
        document.body.classList.remove('light-mode');
        localStorage.setItem('theme', 'dark');
    }
}

// Load user info
async function loadUser() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            const user = await response.json();
            document.getElementById('user-name').textContent = user.name || 'User';
        } else if (response.status === 401) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading user:', error);
    }
}

// Logout
function logout() {
    window.location.href = '/logout';
}

// Switch mode
function switchMode(mode) {
    currentMode = mode;
    
    // Update tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
    
    // Update panels
    document.querySelectorAll('.mode-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    document.getElementById(`${mode}-mode`).classList.add('active');
    
    // Initialize camera if switching to camera mode
    if (mode === 'camera' && !videoStream) {
        initCamera();
    }
}

// Initialize camera
async function initCamera() {
    try {
        const video = document.getElementById('video');
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'user' } 
        });
        video.srcObject = videoStream;
    } catch (error) {
        showError('Camera access denied. Please enable camera permissions.');
        console.error('Camera error:', error);
    }
}

// Detect mood from camera
async function detectCamera() {
    showLoading('Detecting your mood...');
    
    try {
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0);
        
        const imageData = canvas.toDataURL('image/jpeg');
        
        const response = await fetch('/api/detect_camera', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayCameraResult(data);
            await autoPlay();
        } else {
            showError(data.error || 'Detection failed');
        }
    } catch (error) {
        showError('Error detecting mood: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Display camera result
function displayCameraResult(data) {
    const resultDiv = document.getElementById('camera-result');
    
    const moodEmojis = {
        'happy': '😊',
        'sad': '😢',
        'calm': '😌',
        'angry': '😠',
        'energetic': '⚡',
        'nostalgic': '🌅'
    };
    
    let html = `
        <div class="emotion-result">
            <div class="emotion-icon">${moodEmojis[data.dominant_mood] || '😐'}</div>
            <div class="emotion-label">${data.dominant_mood}</div>
            <div class="emotion-confidence">Confidence: ${(data.confidence * 100).toFixed(1)}%</div>
        </div>
    `;
    
    if (data.all_emotions) {
        html += '<div class="emotion-bars">';
        for (const [emotion, score] of Object.entries(data.all_emotions)) {
            html += `
                <div class="emotion-bar">
                    <div class="emotion-bar-label">${emotion}</div>
                    <div class="emotion-bar-container">
                        <div class="emotion-bar-fill" style="width: ${score * 100}%"></div>
                    </div>
                    <div class="emotion-bar-value">${(score * 100).toFixed(0)}%</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    resultDiv.innerHTML = html;
}

// Detect mood from text
async function detectText() {
    const text = document.getElementById('text-input').value.trim();
    
    if (!text) {
        showError('Please enter some text');
        return;
    }
    
    showLoading('Analyzing your feelings...');
    
    try {
        const response = await fetch('/api/detect_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayTextResult(data);
            await autoPlay();
        } else {
            showError(data.error || 'Analysis failed');
        }
    } catch (error) {
        showError('Error analyzing text: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Display text result
function displayTextResult(data) {
    const resultDiv = document.getElementById('text-result');
    
    const moodEmojis = {
        'happy': '😊',
        'sad': '😢',
        'calm': '😌',
        'angry': '😠',
        'energetic': '⚡',
        'nostalgic': '🌅'
    };
    
    let html = `
        <div class="emotion-result">
            <div class="emotion-icon">${moodEmojis[data.dominant_mood] || '😐'}</div>
            <div class="emotion-label">${data.dominant_mood}</div>
            <div class="emotion-confidence">Confidence: ${(data.confidence * 100).toFixed(1)}%</div>
        </div>
    `;
    
    if (data.emotions) {
        html += '<div class="emotion-bars">';
        const sorted = Object.entries(data.emotions).sort((a, b) => b[1] - a[1]);
        for (const [emotion, score] of sorted) {
            html += `
                <div class="emotion-bar">
                    <div class="emotion-bar-label">${emotion}</div>
                    <div class="emotion-bar-container">
                        <div class="emotion-bar-fill" style="width: ${score * 100}%"></div>
                    </div>
                    <div class="emotion-bar-value">${(score * 100).toFixed(0)}%</div>
                </div>
            `;
        }
        html += '</div>';
    }
    
    resultDiv.innerHTML = html;
}

// Select mood manually
async function selectMood(mood) {
    showLoading('Setting mood...');
    
    try {
        const response = await fetch('/api/set_mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mood })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayManualResult(mood);
            await autoPlay();
        } else {
            showError(data.error || 'Failed to set mood');
        }
    } catch (error) {
        showError('Error setting mood: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Display manual result
function displayManualResult(mood) {
    const resultDiv = document.getElementById('manual-result');
    
    const moodEmojis = {
        'happy': '😊',
        'sad': '😢',
        'calm': '😌',
        'angry': '😠',
        'energetic': '⚡',
        'nostalgic': '🌅'
    };
    
    resultDiv.innerHTML = `
        <div class="emotion-result">
            <div class="emotion-icon">${moodEmojis[mood] || '😐'}</div>
            <div class="emotion-label">${mood}</div>
        </div>
    `;
}

// Search song
async function searchSong() {
    const query = document.getElementById('search-input').value.trim();
    
    if (!query) {
        showError('Please enter a song name');
        return;
    }
    
    showLoading('Searching...');
    
    try {
        const response = await fetch('/api/search_song', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displaySearchResult(data);
            await playSearchResult(data.track_uri);
        } else {
            showError(data.error || 'Search failed');
        }
    } catch (error) {
        showError('Error searching: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Handle search enter key
function handleSearchEnter(event) {
    if (event.key === 'Enter') {
        searchSong();
    }
}

// Display search result
function displaySearchResult(data) {
    const resultDiv = document.getElementById('search-result');
    
    resultDiv.innerHTML = `
        <div class="emotion-result">
            <div class="emotion-label">${data.name}</div>
            <div class="emotion-confidence">${data.artist}</div>
        </div>
    `;
}

// Play search result
async function playSearchResult(trackUri) {
    showLoading('Playing...');
    
    try {
        const response = await fetch('/api/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mode: 'search',
                track_uri: trackUri
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setTimeout(updateCurrentTrack, 2000);
        } else {
            showError(data.error || 'Playback failed');
        }
    } catch (error) {
        showError('Error playing: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Auto play after mood detection
async function autoPlay() {
    showLoading('Finding perfect music...');
    
    try {
        const response = await fetch('/api/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'mood' })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const nowPlaying = document.getElementById('now-playing');
            nowPlaying.style.display = 'block';
            setTimeout(updateCurrentTrack, 2000);
        } else {
            showError(data.error || 'Playback failed');
        }
    } catch (error) {
        showError('Error playing music: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Update current track
async function updateCurrentTrack() {
    try {
        const response = await fetch('/api/current_track');
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            // Not JSON, probably redirected to login
            console.log('Session expired, please login again');
            return;
        }
        
        const data = await response.json();
        
        if (response.ok && data.playing) {
            const nowPlaying = document.getElementById('now-playing');
            nowPlaying.style.display = 'block';
            
            // Update track info
            document.getElementById('track-image').src = data.image || '';
            document.getElementById('track-name').textContent = data.name;
            document.getElementById('track-artist').textContent = data.artist;
            document.getElementById('track-album').textContent = data.album;
            
            // Update play/pause button
            updatePlayPauseButton(data.is_playing);
            
            // Update track data for smooth animation
            trackData.progress_ms = data.progress_ms;
            trackData.duration_ms = data.duration_ms;
            trackData.lastUpdate = Date.now();
            trackData.isPlaying = data.is_playing;
            
            // Start smooth progress animation if not already running
            if (!progressAnimationFrame && data.is_playing) {
                animateProgress();
            }
        }
    } catch (error) {
        // Silently fail - don't spam console with errors
        // This happens when no music is playing or session expired
    }
}

// Update play/pause button icon
function updatePlayPauseButton(isPlaying) {
    const playIcon = document.getElementById('play-icon');
    const pauseIcon = document.getElementById('pause-icon');
    
    if (isPlaying) {
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
    } else {
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
    }
}

// Playback Controls
async function togglePlayPause() {
    try {
        const response = await fetch('/api/playback/play-pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            trackData.isPlaying = data.is_playing;
            updatePlayPauseButton(data.is_playing);
            
            if (data.is_playing && !progressAnimationFrame) {
                trackData.lastUpdate = Date.now();
                animateProgress();
            } else if (!data.is_playing && progressAnimationFrame) {
                cancelAnimationFrame(progressAnimationFrame);
                progressAnimationFrame = null;
            }
            
            // Update track info after a short delay
            setTimeout(updateCurrentTrack, 500);
        } else {
            showError(data.error || 'Playback control failed');
        }
    } catch (error) {
        showError('Error controlling playback: ' + error.message);
    }
}

async function nextTrack() {
    try {
        showLoading('Skipping to next track...');
        
        const response = await fetch('/api/playback/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Reset progress animation
            if (progressAnimationFrame) {
                cancelAnimationFrame(progressAnimationFrame);
                progressAnimationFrame = null;
            }
            
            // Update track info after delay
            setTimeout(updateCurrentTrack, 1500);
        } else {
            showError(data.error || 'Failed to skip track');
        }
    } catch (error) {
        showError('Error skipping track: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function previousTrack() {
    try {
        showLoading('Going to previous track...');
        
        const response = await fetch('/api/playback/previous', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Reset progress animation
            if (progressAnimationFrame) {
                cancelAnimationFrame(progressAnimationFrame);
                progressAnimationFrame = null;
            }
            
            // Update track info after delay
            setTimeout(updateCurrentTrack, 1500);
        } else {
            showError(data.error || 'Failed to go to previous track');
        }
    } catch (error) {
        showError('Error going to previous track: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Animate progress bar smoothly
function animateProgress() {
    if (!trackData.isPlaying || trackData.duration_ms === 0) {
        progressAnimationFrame = null;
        return;
    }
    
    // Calculate current progress based on time elapsed since last update
    const now = Date.now();
    const elapsed = now - trackData.lastUpdate;
    const currentProgress = trackData.progress_ms + elapsed;
    
    // Don't go over duration
    if (currentProgress >= trackData.duration_ms) {
        trackData.progress_ms = trackData.duration_ms;
        progressAnimationFrame = null;
        return;
    }
    
    // Update progress bar
    const progress = (currentProgress / trackData.duration_ms) * 100;
    document.getElementById('progress-bar').style.width = progress + '%';
    
    // Update time displays
    document.getElementById('current-time').textContent = formatTime(currentProgress);
    document.getElementById('total-time').textContent = formatTime(trackData.duration_ms);
    
    // Continue animation
    progressAnimationFrame = requestAnimationFrame(animateProgress);
}

// Start polling current track
function startCurrentTrackPolling() {
    // Poll every 2 seconds for track updates
    currentTrackInterval = setInterval(updateCurrentTrack, 2000);
}

// Format time
function formatTime(ms) {
    const seconds = Math.floor(ms / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Show loading
function showLoading(text = 'Loading...') {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading').style.display = 'flex';
}

// Hide loading
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Show error
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
    if (currentTrackInterval) {
        clearInterval(currentTrackInterval);
    }
    if (progressAnimationFrame) {
        cancelAnimationFrame(progressAnimationFrame);
    }
});
