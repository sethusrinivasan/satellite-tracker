#!/usr/bin/env bash
set -e

# POSIX-compliant script directory resolution
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check for optional Docker deployment flag
if [ "$1" = "--docker" ] || [ "$1" = "docker" ]; then
    echo "🐳 Deploying Satellite TLE Tracker in local Docker container..."
    if ! command -v docker &> /dev/null; then
        echo "❌ Error: Docker is not installed or not in PATH."
        exit 1
    fi
    echo "🔨 Building Docker image (satellite-tracker:latest)..."
    docker build -t satellite-tracker:latest .
    
    echo "🚀 Launching container at http://localhost:5000 ..."
    if [ -f ".env" ]; then
        exec docker run -it --rm -p 5000:5000 --env-file .env satellite-tracker:latest
    else
        exec docker run -it --rm -p 5000:5000 satellite-tracker:latest
    fi
fi

echo "🛰️ Starting Satellite TLE Tracker (Local Python Virtualenv)..."
echo "💡 Hint: Run './run.sh --docker' to deploy in a local Docker container instead."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "📥 Installing dependencies from requirements.txt..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Copy .env.example if .env is missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚙️ Creating default .env configuration file..."
    cp .env.example .env
fi

# Activate virtual environment (POSIX '.' syntax works in sh, dash, zsh, and bash)
. venv/bin/activate

# Start the Flask development server
echo "🚀 Web server listening at http://localhost:5000"
exec python3 run.py
