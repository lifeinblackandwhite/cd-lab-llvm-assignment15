#!/usr/bin/env bash
set -e

if [ ! -d "myvenv" ]; then
    echo "Virtual environment not found. Please run ./build.sh first."
    exit 1
fi

source myvenv/bin/activate

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "WARNING: ANTHROPIC_API_KEY is not set. Failure analysis will crash if an error occurs."
fi

echo "==========================================="
echo "Running main testing pipeline (main.py)"
echo "==========================================="
python3 src/main.py

echo "==========================================="
echo "Running semantic correctness & repair pipeline (secomd.py)"
echo "==========================================="
python3 src/secomd.py
