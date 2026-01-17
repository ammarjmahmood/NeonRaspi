# Son of Anton - AI Voice Assistant for Raspberry Pi

A premium voice-controlled AI assistant with Google Gemini, ElevenLabs natural voice, Spotify integration, and MCP server support.

## ✨ Features

- **🎤 Always Listening** - Wake word detection ("Hey Jarvis" temporarily, custom wake word coming soon)
- **🧠 Google Gemini AI** - Powerful conversational AI for answering questions
- **🔊 ElevenLabs Voice** - Natural, human-like voice responses
- **🎵 Spotify Integration** - Control music, view now playing with album art & lyrics
- **📅 MCP Integrations** - Calendar, weather, web content, and more
- **🖥️ Modern Web UI** - Beautiful dark theme with smooth animations
- **🍓 Raspberry Pi Native** - Optimized for Pi 4/5 with kiosk mode

## 🚀 Quick Start

### On Raspberry Pi

```bash
# Clone the repository
git clone https://github.com/ammarjmahmood/NeonRaspi.git
cd NeonRaspi

# Run the install script
chmod +x install.sh
./install.sh

# Configure your API keys
cp .env.example .env
nano .env  # Add your API keys

# Start the assistant
./start.sh
```

### On Mac (for development/testing)

```bash
# Clone the repository
git clone https://github.com/ammarjmahmood/NeonRaspi.git
cd NeonRaspi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your API keys
cp .env.example .env
# Edit .env with your keys

# Start the server
python backend/main.py
```

Then open http://localhost:8000 in your browser.

## 🔑 Required API Keys

| Service | Get Key From | Purpose |
|---------|--------------|---------|
| Google Gemini | [Google AI Studio](https://aistudio.google.com/apikey) | AI responses |
| ElevenLabs | [ElevenLabs](https://elevenlabs.io) | Voice synthesis |
| Spotify | [Spotify Developer](https://developer.spotify.com/dashboard) | Music control |

## 📁 Project Structure

```
son-of-anton/
├── backend/          # Python FastAPI server
│   ├── main.py       # Entry point
│   ├── wake_word.py  # Wake word detection
│   ├── gemini.py     # Gemini AI client
│   ├── tts.py        # ElevenLabs TTS
│   └── spotify.py    # Spotify integration
├── frontend/         # Web UI
│   ├── index.html    # Main page
│   ├── css/          # Styles
│   └── js/           # Scripts
├── install.sh        # Pi setup script
└── start.sh          # Launch script
```

## 🎨 UI Preview

The interface features:
- Animated listening orb that reacts to voice
- Now Playing widget with album art
- Synced lyrics display
- Conversation history
- Status indicators

## 🛠️ MCP Integrations

- **Spotify** - Play music, control playback
- **Google Calendar** - View and add events
- **Weather** - Current conditions and forecasts
- **Web Fetch** - Read Reddit threads, articles
- **Time** - Current time and timezones

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
