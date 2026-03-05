#!/bin/bash
# run.sh — Start TranSignal
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="$SCRIPT_DIR/python"

# Activate the virtual environment
source "$PYTHON_DIR/.venv/bin/activate"

# Launch Streamlit
cd "$PYTHON_DIR"
streamlit run app.py --browser.gatherUsageStats false
