#!/bin/bash
# run.sh — Start TranSignal
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/python"

# Activate the virtual environment
source "$PYTHON_DIR/.venv/bin/activate"

cd "$PYTHON_DIR"

echo "🚀 Starting FastAPI Backend (which includes the autonomous daemon)..."
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 &
DAEMON_PID=$!

function cleanup {
    echo ""
    echo "🛑 Stopping Background Daemon (PID $DAEMON_PID)..."
    kill $DAEMON_PID 2>/dev/null || true
    echo "Done."
    exit 0
}

# Ensure the daemon is killed when this script exits or is interrupted
trap cleanup EXIT INT TERM

echo "🌐 Launching Streamlit Command Center..."
python3 -m streamlit run app.py --browser.gatherUsageStats false
