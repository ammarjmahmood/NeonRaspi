#!/bin/bash
# ============================================
# Neon Pi - Start Script
# ============================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${PURPLE}"
cat << "EOF"
    _   __                     ____  _ 
   / | / /__  ____  ____     / __ \(_)
  /  |/ / _ \/ __ \/ __ \   / /_/ / / 
 / /|  /  __/ /_/ / / / /  / ____/ /  
/_/ |_/\___/\____/_/ /_/  /_/   /_/   
EOF
echo -e "${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ No .env file found. Creating from example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}  Please edit .env and add your API keys${NC}"
    echo ""
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠ Virtual environment not found. Run install.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Neon Pi...${NC}"
echo -e "  Server: http://localhost:8000"
echo -e "  Press Ctrl+C to stop"
echo ""

# Start the server
python -m backend.main
