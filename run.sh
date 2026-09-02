#!/usr/bin/env bash
set -e

# POSIX-compliant script directory resolution
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛰️ Starting Satellite TLE Tracker..."

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
