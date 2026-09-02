#!/usr/bin/env bash
set -e

# Ensure common system binary paths are present in PATH
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# POSIX-compliant script directory resolution
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check for optional Docker deployment flag
if [ "$1" = "--docker" ] || [ "$1" = "docker" ]; then
    echo "🐳 Deploying Satellite TLE Tracker in local Docker container..."
    
    # Locate docker executable
    DOCKER_BIN="$(command -v docker || echo "")"
    if [ -z "$DOCKER_BIN" ] && [ -x "/usr/local/bin/docker" ]; then
        DOCKER_BIN="/usr/local/bin/docker"
    elif [ -z "$DOCKER_BIN" ] && [ -x "/usr/bin/docker" ]; then
        DOCKER_BIN="/usr/bin/docker"
    fi

    if [ -z "$DOCKER_BIN" ] || [ ! -x "$DOCKER_BIN" ]; then
        echo "❌ Error: Docker executable not found in PATH or standard paths (/usr/local/bin/docker, /usr/bin/docker)."
        exit 1
    fi

    echo "🔨 Building Docker image using $DOCKER_BIN (satellite-tracker:latest)..."
    "$DOCKER_BIN" build -t satellite-tracker:latest .
    
    echo "🚀 Launching container at http://localhost:5000 ..."
    if [ -f ".env" ]; then
        exec "$DOCKER_BIN" run -it --rm -p 5000:5000 --env-file .env satellite-tracker:latest
    else
        exec "$DOCKER_BIN" run -it --rm -p 5000:5000 satellite-tracker:latest
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
