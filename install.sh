#!/bin/bash
# ============================================
# Son of Anton - Installation Script
# One-command setup for Raspberry Pi
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ASCII Art
echo -e "${PURPLE}"
cat << "EOF"
   _____               ___   __   ___        __            
  / ___/__  ___    ___/ _/  / /  / _ | ___  / /____  ___   
  \__ \/ _ \/ _ \  / _  /  / /__/ __ |/ _ \/ __/ _ \/ _ \  
 ___/ / /__/ // / /_//_/  /____/_/ |_/_//_/\__/\___/_//_/  
/____/\___/\___/                                           
                                                           
    AI Voice Assistant for Raspberry Pi
EOF
echo -e "${NC}"

# ============================================
# System Detection
# ============================================
echo -e "${BLUE}[1/8] Detecting system...${NC}"

IS_RASPBERRY_PI=false
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        IS_RASPBERRY_PI=true
        echo -e "${GREEN}✓ Detected: $MODEL${NC}"
    fi
fi

if [ "$IS_RASPBERRY_PI" = false ]; then
    echo -e "${YELLOW}⚠ Not running on Raspberry Pi - some features may not work${NC}"
    echo -e "${YELLOW}  Continuing with development mode...${NC}"
fi

# ============================================
# Create directories
# ============================================
echo -e "${BLUE}[2/8] Creating directories...${NC}"

ANTON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$ANTON_DIR/logs"
mkdir -p "$ANTON_DIR/models"
mkdir -p "$ANTON_DIR/credentials"

echo -e "${GREEN}✓ Directories created${NC}"

# ============================================
# System Dependencies (Raspberry Pi only)
# ============================================
echo -e "${BLUE}[3/8] Installing system dependencies...${NC}"

if [ "$IS_RASPBERRY_PI" = true ] || [ -f /etc/debian_version ]; then
    # Detect package manager
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            python3-pip \
            python3-venv \
            python3-dev \
            portaudio19-dev \
            libsndfile1 \
            ffmpeg \
            chromium-browser \
            unclutter \
            xdotool
        echo -e "${GREEN}✓ System dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠ apt not found, skipping system packages${NC}"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        echo -e "${YELLOW}Installing macOS dependencies via Homebrew...${NC}"
        brew install portaudio ffmpeg || true
        echo -e "${GREEN}✓ macOS dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠ Homebrew not found. Install portaudio and ffmpeg manually.${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Unknown OS, skipping system dependencies${NC}"
fi

# ============================================
# Python Virtual Environment
# ============================================
echo -e "${BLUE}[4/8] Setting up Python environment...${NC}"

cd "$ANTON_DIR"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "  Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

# ============================================
# Python Dependencies
# ============================================
echo -e "${BLUE}[5/8] Installing Python packages...${NC}"

pip install -r requirements.txt

echo -e "${GREEN}✓ Python packages installed${NC}"

# ============================================
# Download Models
# ============================================
echo -e "${BLUE}[6/8] Downloading AI models...${NC}"

# Download OpenWakeWord models
python3 << 'PYEOF'
import os
try:
    from openwakeword.model import Model
    print("Downloading wake word models...")
    model = Model(wakeword_models=["hey_jarvis"])
    print("✓ Wake word models downloaded")
except Exception as e:
    print(f"⚠ Wake word model download: {e}")

try:
    from faster_whisper import WhisperModel
    print("Downloading Whisper model (base)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("✓ Whisper model downloaded")
except Exception as e:
    print(f"⚠ Whisper model download: {e}")
PYEOF

echo -e "${GREEN}✓ Models ready${NC}"

# ============================================
# Environment Configuration
# ============================================
echo -e "${BLUE}[7/8] Setting up configuration...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Created .env file - please add your API keys:${NC}"
    echo -e "   ${PURPLE}nano $ANTON_DIR/.env${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# ============================================
# Systemd Service (Raspberry Pi only)
# ============================================
echo -e "${BLUE}[8/8] Setting up autostart...${NC}"

if [ "$IS_RASPBERRY_PI" = true ]; then
    # Create systemd service file
    sudo tee /etc/systemd/system/son-of-anton.service > /dev/null << SERVICEEOF
[Unit]
Description=Son of Anton Voice Assistant
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$ANTON_DIR
Environment="PATH=$ANTON_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$ANTON_DIR/venv/bin/python -m backend.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

    # Create kiosk autostart
    mkdir -p ~/.config/autostart
    cat > ~/.config/autostart/anton-kiosk.desktop << KIOSKEOF
[Desktop Entry]
Type=Application
Name=Son of Anton Kiosk
Exec=bash $ANTON_DIR/scripts/kiosk.sh
X-GNOME-Autostart-enabled=true
KIOSKEOF

    # Create kiosk script
    mkdir -p "$ANTON_DIR/scripts"
    cat > "$ANTON_DIR/scripts/kiosk.sh" << 'KIOSKSCRIPT'
#!/bin/bash
# Wait for network and server to start
sleep 10

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor
unclutter -idle 0.5 -root &

# Start Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --enable-features=OverlayScrollbar \
    --start-fullscreen \
    http://localhost:8000
KIOSKSCRIPT
    chmod +x "$ANTON_DIR/scripts/kiosk.sh"

    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable son-of-anton.service
    
    echo -e "${GREEN}✓ Systemd service and kiosk autostart configured${NC}"
else
    echo -e "${YELLOW}⚠ Skipping systemd setup (not on Raspberry Pi)${NC}"
fi

# ============================================
# Complete!
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Son of Anton Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Add your API keys to .env:"
echo -e "     ${PURPLE}nano $ANTON_DIR/.env${NC}"
echo ""
echo -e "  2. Start Son of Anton:"
echo -e "     ${PURPLE}./start.sh${NC}"
echo ""
echo -e "  3. Open in browser:"
echo -e "     ${PURPLE}http://localhost:8000${NC}"
echo ""
if [ "$IS_RASPBERRY_PI" = true ]; then
    echo -e "  ${GREEN}On next reboot, Anton will start automatically!${NC}"
fi
echo ""
