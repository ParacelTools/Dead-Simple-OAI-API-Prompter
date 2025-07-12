#!/bin/bash
echo "== Parachat launcher =="

# Create .venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "-- Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install Flask if not installed
if ! pip show flask >/dev/null 2>&1; then
    echo "-- Installing Flask..."
    pip install flask
    pip install requests
fi

# Run app.py
echo "-- Launching app.py ..."
python3 app.py