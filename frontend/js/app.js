/**
 * Neon Pi - Main Application JavaScript
 * Handles WebSocket connection, UI state, and user interactions.
 */

// ============================================
// State Management
// ============================================
const state = {
    connected: false,
    spotifyConnected: false,
    currentState: 'idle', // idle, listening, processing, speaking
    nowPlaying: null,
    conversationHistory: []
};

// ============================================
// DOM Elements
// ============================================
const elements = {
    // Orb
    orb: document.getElementById('orb'),
    orbPulse: document.getElementById('orbPulse'),
    
    // Status
    statusText: document.getElementById('statusText'),
    statusSubtitle: document.getElementById('statusSubtitle'),
    connectionStatus: document.getElementById('connectionStatus'),
    timeDisplay: document.getElementById('timeDisplay'),
    
    // Transcript
    transcriptContainer: document.getElementById('transcriptContainer'),
    userBubble: document.getElementById('userBubble'),
    userText: document.getElementById('userText'),
    neonBubble: document.getElementById('neonBubble'),
    neonText: document.getElementById('neonText'),
    
    // Spotify
    spotifyPanel: document.getElementById('spotifyPanel'),
    albumArt: document.getElementById('albumArt'),
    albumPlaceholder: document.getElementById('albumPlaceholder'),
    trackName: document.getElementById('trackName'),
    artistName: document.getElementById('artistName'),
    progressFill: document.getElementById('progressFill'),
    currentTime: document.getElementById('currentTime'),
    totalTime: document.getElementById('totalTime'),
    spotifyConnectBtn: document.getElementById('spotifyConnectBtn'),
    lyricsContent: document.getElementById('lyricsContent'),
    
    // History
    historyList: document.getElementById('historyList'),
    
    // Buttons
    manualTrigger: document.getElementById('manualTrigger'),
    
    // Audio
    audioPlayer: document.getElementById('audioPlayer')
};

// ============================================
// WebSocket Connection
// ============================================
let ws = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 10;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('[WS] Connecting to:', wsUrl);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('[WS] Connected');
        state.connected = true;
        reconnectAttempts = 0;
        updateConnectionStatus(true);
    };
    
    ws.onclose = (event) => {
        console.log('[WS] Disconnected', event.code);
        state.connected = false;
        updateConnectionStatus(false);
        
        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
            setTimeout(connectWebSocket, delay);
        }
    };
    
    ws.onerror = (error) => {
        console.error('[WS] Error:', error);
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (e) {
            console.error('[WS] Parse error:', e);
        }
    };
}

function sendMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    }
}

// ============================================
// Message Handlers
// ============================================
function handleMessage(message) {
    console.log('[WS] Message:', message.type);
    
    switch (message.type) {
        case 'connected':
            state.spotifyConnected = message.spotify_authenticated;
            updateSpotifyStatus();
            break;
            
        case 'state_update':
            updateState(message.state, message.data);
            break;
            
        case 'transcript':
            showTranscript(message.text, message.is_final);
            break;
            
        case 'response':
            showResponse(message.text);
            break;
            
        case 'spotify':
            updateNowPlaying(message.data);
            break;
            
        case 'audio':
            playAudio(message.data);
            break;
            
        case 'error':
            showError(message.message);
            break;
    }
}

// ============================================
// State Updates
// ============================================
function updateState(newState, data = {}) {
    state.currentState = newState;
    
    // Update orb class
    elements.orb.className = 'orb ' + newState;
    
    // Update status text
    switch (newState) {
        case 'idle':
            elements.statusText.textContent = 'Say "Hey Jarvis" to wake me up';
            elements.statusSubtitle.textContent = 'Listening for wake word...';
            elements.transcriptContainer.classList.remove('visible');
            break;
            
        case 'listening':
            elements.statusText.textContent = "I'm listening...";
            elements.statusSubtitle.textContent = 'Speak your command';
            break;
            
        case 'processing':
            elements.statusText.textContent = 'Processing...';
            elements.statusSubtitle.textContent = 'Understanding your request';
            break;
            
        case 'thinking':
            elements.statusText.textContent = 'Thinking...';
            elements.statusSubtitle.textContent = 'Generating response';
            break;
            
        case 'speaking':
            elements.statusText.textContent = 'Speaking...';
            elements.statusSubtitle.textContent = '';
            break;
    }
    
    // Handle audio level visualization
    if (data.level !== undefined) {
        visualizeAudioLevel(data.level);
    }
}

function visualizeAudioLevel(level) {
    // Scale orb based on audio level
    const scale = 1 + (level / 1000) * 0.2;
    elements.orb.style.transform = `scale(${Math.min(scale, 1.3)})`;
}

// ============================================
// Transcript Display
// ============================================
function showTranscript(text, isFinal) {
    elements.transcriptContainer.classList.add('visible');
    elements.userText.textContent = text;
    elements.userBubble.style.display = 'block';
    elements.neonBubble.style.display = 'none';
    
    if (isFinal) {
        // Add to history
        addToHistory(text, null);
    }
}

function showResponse(text) {
    elements.neonText.textContent = text;
    elements.neonBubble.style.display = 'block';
    
    // Update history with response
    updateHistoryResponse(text);
}

// ============================================
// Conversation History
// ============================================
function addToHistory(userText, response) {
    const item = {
        user: userText,
        response: response,
        timestamp: new Date()
    };
    state.conversationHistory.push(item);
    renderHistory();
}

function updateHistoryResponse(response) {
    if (state.conversationHistory.length > 0) {
        state.conversationHistory[state.conversationHistory.length - 1].response = response;
        renderHistory();
    }
}

function renderHistory() {
    if (state.conversationHistory.length === 0) {
        elements.historyList.innerHTML = `
            <div class="history-empty">
                <p>No conversations yet</p>
                <p class="history-hint">Say "Hey Jarvis" to start</p>
            </div>
        `;
        return;
    }
    
    elements.historyList.innerHTML = state.conversationHistory
        .slice(-10) // Show last 10
        .reverse()
        .map(item => `
            <div class="history-item">
                <div class="history-item-user">${escapeHtml(item.user)}</div>
                ${item.response ? `<div class="history-item-response">${escapeHtml(item.response)}</div>` : ''}
            </div>
        `)
        .join('');
}

// ============================================
// Spotify Integration
// ============================================
function updateNowPlaying(data) {
    if (!data) {
        elements.trackName.textContent = 'Not Playing';
        elements.artistName.textContent = 'Connect to Spotify';
        elements.albumArt.classList.remove('loaded');
        elements.albumPlaceholder.style.display = 'flex';
        return;
    }
    
    state.nowPlaying = data;
    
    // Update track info
    if (data.is_podcast) {
        elements.trackName.textContent = data.episode_name || 'Unknown Episode';
        elements.artistName.textContent = data.show_name || 'Podcast';
    } else {
        elements.trackName.textContent = data.track_name || 'Unknown Track';
        elements.artistName.textContent = data.artist_name || 'Unknown Artist';
    }
    
    // Update album art
    if (data.image_url) {
        elements.albumArt.src = data.image_url;
        elements.albumArt.onload = () => {
            elements.albumArt.classList.add('loaded');
            elements.albumPlaceholder.style.display = 'none';
        };
    }
    
    // Update progress
    if (data.duration_ms > 0) {
        const progress = (data.progress_ms / data.duration_ms) * 100;
        elements.progressFill.style.width = `${progress}%`;
        elements.currentTime.textContent = formatTime(data.progress_ms);
        elements.totalTime.textContent = formatTime(data.duration_ms);
    }
}

function updateSpotifyStatus() {
    if (state.spotifyConnected) {
        elements.spotifyConnectBtn.classList.add('connected');
        elements.spotifyConnectBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
            </svg>
            <span>Connected</span>
        `;
    } else {
        elements.spotifyConnectBtn.classList.remove('connected');
    }
}

async function connectSpotify() {
    try {
        const response = await fetch('/api/spotify/auth');
        const data = await response.json();
        
        if (data.auth_url) {
            // Open Spotify auth in new window
            const authWindow = window.open(
                data.auth_url,
                'Spotify Auth',
                'width=500,height=700,menubar=no,toolbar=no'
            );
            
            // Poll for auth completion
            const pollTimer = setInterval(() => {
                if (authWindow.closed) {
                    clearInterval(pollTimer);
                    // Refresh status
                    window.location.reload();
                }
            }, 1000);
        }
    } catch (error) {
        console.error('[Spotify] Auth error:', error);
    }
}

// ============================================
// Audio Playback
// ============================================
function playAudio(hexData) {
    try {
        // Convert hex string to Uint8Array
        const bytes = new Uint8Array(hexData.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
        
        // Create blob and URL
        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        const url = URL.createObjectURL(blob);
        
        // Play audio
        elements.audioPlayer.src = url;
        elements.audioPlayer.play()
            .then(() => console.log('[Audio] Playing'))
            .catch(e => console.error('[Audio] Play error:', e));
        
        // Clean up URL after playback
        elements.audioPlayer.onended = () => {
            URL.revokeObjectURL(url);
        };
    } catch (error) {
        console.error('[Audio] Playback error:', error);
    }
}

// ============================================
// UI Updates
// ============================================
function updateConnectionStatus(connected) {
    if (connected) {
        elements.connectionStatus.classList.add('connected');
        elements.connectionStatus.classList.remove('error');
        elements.connectionStatus.querySelector('.status-label').textContent = 'Connected';
    } else {
        elements.connectionStatus.classList.remove('connected');
        elements.connectionStatus.classList.add('error');
        elements.connectionStatus.querySelector('.status-label').textContent = 'Reconnecting...';
    }
}

function updateTime() {
    const now = new Date();
    elements.timeDisplay.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

function showError(message) {
    console.error('[Error]', message);
    elements.statusText.textContent = 'Error';
    elements.statusSubtitle.textContent = message;
    
    // Reset after 3 seconds
    setTimeout(() => {
        updateState('idle');
    }, 3000);
}

// ============================================
// Utility Functions
// ============================================
function formatTime(ms) {
    const seconds = Math.floor((ms / 1000) % 60);
    const minutes = Math.floor((ms / (1000 * 60)) % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Event Listeners
// ============================================
function setupEventListeners() {
    // Manual trigger button
    elements.manualTrigger.addEventListener('click', () => {
        console.log('[UI] Manual trigger clicked');
        sendMessage({ type: 'start_listening' });
    });
    
    // Spotify connect button
    elements.spotifyConnectBtn.addEventListener('click', () => {
        if (!state.spotifyConnected) {
            connectSpotify();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Space bar to trigger listening
        if (e.code === 'Space' && e.target === document.body) {
            e.preventDefault();
            sendMessage({ type: 'start_listening' });
        }
    });
}

// ============================================
// Background Particles
// ============================================
function createParticles() {
    const container = document.getElementById('particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 4 + 1}px;
            height: ${Math.random() * 4 + 1}px;
            background: rgba(99, 102, 241, ${Math.random() * 0.3 + 0.1});
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation: float ${Math.random() * 10 + 10}s linear infinite;
            animation-delay: -${Math.random() * 10}s;
        `;
        container.appendChild(particle);
    }
    
    // Add floating animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes float {
            0%, 100% { 
                transform: translate(0, 0) rotate(0deg); 
                opacity: 0.3;
            }
            25% { 
                transform: translate(30px, -30px) rotate(90deg); 
                opacity: 0.8;
            }
            50% { 
                transform: translate(-20px, -60px) rotate(180deg); 
                opacity: 0.5;
            }
            75% { 
                transform: translate(-40px, -30px) rotate(270deg); 
                opacity: 0.7;
            }
        }
    `;
    document.head.appendChild(style);
}

// ============================================
// Initialization
// ============================================
function init() {
    console.log('[Neon] Initializing...');
    
    // Create background particles
    createParticles();
    
    // Setup event listeners
    setupEventListeners();
    
    // Update time every minute
    updateTime();
    setInterval(updateTime, 60000);
    
    // Connect WebSocket
    connectWebSocket();
    
    // Render initial history
    renderHistory();
    
    console.log('[Neon] Ready!');
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
