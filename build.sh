#!/usr/bin/env bash
set -e

echo "Building environment..."
python3 -m venv myvenv
source myvenv/bin/activate
pip install anthropic

echo "==========================================="
echo "Build complete."
echo "Please ensure you have set your Anthropic API key:"
echo "export ANTHROPIC_API_KEY='your_api_key_here'"
echo "==========================================="
