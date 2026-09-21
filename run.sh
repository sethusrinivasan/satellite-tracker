#!/usr/bin/env bash
set -e

# Ensure common system binary paths are present in PATH
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# POSIX-compliant script directory resolution
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================================="
echo "🛰️  SatTrack Launch Manager — Execution Mode Selection"
echo "=========================================================================="
echo "  [1] Local Dev Environment (Default - Native Python Virtualenv)"
echo "      → Usage: ./run.sh  OR  ./run.sh --local"
echo ""
echo "  [2] Local Docker Container Environment"
echo "      → Usage: ./run.sh --docker"
echo ""
echo "  [3] Docker Compose (SQLite, first-launch wizard)"
echo "      → Usage: ./run.sh --compose"
echo ""
echo "  [4] Docker Compose + PostgreSQL"
echo "      → Usage: ./run.sh --compose-postgres"
echo ""
echo "  [5] Docker Compose tests"
echo "      → Usage: ./run.sh --compose-test"
echo "      → Usage: ./run.sh --compose-test-postgres"
echo "=========================================================================="

# Host UID/GID so Compose does not write instance/ as root (breaks ./run.sh --local).
export SATTRACK_UID="$(id -u)"
export SATTRACK_GID="$(id -g)"

# Check for Docker Compose workflows
if [ "$1" = "--compose" ] || [ "$1" = "compose" ]; then
    echo ""
    echo "🐳 Selected Mode: Docker Compose (SQLite / first-launch setup)"
    exec docker compose up --build
fi

if [ "$1" = "--compose-postgres" ] || [ "$1" = "compose-postgres" ]; then
    echo ""
    echo "🐳 Selected Mode: Docker Compose + PostgreSQL"
    exec docker compose --profile postgres up --build
fi

if [ "$1" = "--compose-test" ] || [ "$1" = "compose-test" ]; then
    echo ""
    echo "🧪 Selected Mode: Docker Compose pytest (SQLite)"
    docker compose --profile test build
    exec docker compose --profile test run --rm test
fi

if [ "$1" = "--compose-test-postgres" ] || [ "$1" = "compose-test-postgres" ]; then
    echo ""
    echo "🧪 Selected Mode: Docker Compose pytest (PostgreSQL)"
    docker compose --profile test-postgres build
    exec docker compose --profile test-postgres run --rm test-postgres
fi

# Check for Docker deployment flag
if [ "$1" = "--docker" ] || [ "$1" = "docker" ]; then
    echo ""
    echo "🐳 Selected Mode: Local Docker Container Environment"
    
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

# Default execution mode: Local Dev Environment (Python Virtualenv)
if [ -n "$1" ] && [ "$1" != "--local" ] && [ "$1" != "local" ]; then
    echo "❌ Unknown option: $1"
    echo "   Use --local, --docker, --compose, --compose-postgres, --compose-test, or --compose-test-postgres."
    exit 1
fi

echo ""
echo "💻 Selected Mode: Local Dev Environment (Native Python Virtualenv - Default)"
echo "🚀 Initializing local Python virtual environment..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 was not found. Install Python 3.9+ and retry."
    exit 1
fi

# A previous failed `python3 -m venv` (missing python3-venv/ensurepip) can leave
# a venv/ directory with no activate script or pip. Recreate that skeleton.
venv_ok=0
if [ -x "venv/bin/python" ] && [ -f "venv/bin/activate" ]; then
    venv_ok=1
fi

if [ "$venv_ok" -ne 1 ]; then
    echo "📦 Creating virtual environment (without ensurepip)..."
    python3 -m venv --without-pip --clear venv
fi

if [ ! -x "venv/bin/python" ] || [ ! -f "venv/bin/activate" ]; then
    echo "❌ Could not create a usable virtualenv."
    echo "   On Debian/Ubuntu install:  sudo apt install python3-venv python3-pip"
    echo "   Or run with Docker instead:  sh run.sh --compose"
    exit 1
fi

if [ ! -x "venv/bin/pip" ] && [ ! -x "venv/bin/pip3" ]; then
    echo "📥 Bootstrapping pip into the virtualenv..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | venv/bin/python
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://bootstrap.pypa.io/get-pip.py | venv/bin/python
    else
        echo "❌ pip is missing and neither curl nor wget is available to bootstrap it."
        echo "   Install:  sudo apt install python3-venv python3-pip curl"
        exit 1
    fi
fi

if ! venv/bin/python -c "import flask" >/dev/null 2>&1; then
    echo "📥 Installing dependencies from requirements.txt..."
    venv/bin/python -m pip install --upgrade pip
    venv/bin/python -m pip install -r requirements.txt
fi

# Copy .env.example if .env is missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "⚙️ Creating default .env configuration file..."
    cp .env.example .env
fi

# Start the Flask development server with the venv interpreter (no activate needed)
echo "🚀 Web server listening at http://localhost:5000"
exec venv/bin/python run.py
