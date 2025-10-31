#!/bin/bash
# Installation script for diff2commit CLI

set -e

echo "Installing diff2commit CLI..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.9 or higher is required. Found: $python_version"
    exit 1
fi

# Install using pip
echo "Installing with pip..."
pip3 install diff2commit

# Verify installation
if command -v diff2commit &> /dev/null; then
    echo "✓ diff2commit CLI installed successfully!"
    echo ""
    diff2commit version
    echo ""
    echo "Next steps:"
    echo "1. Set your API key: export D2C_API_KEY='your-key'"
    echo "2. Stage some changes: git add ."
    echo "3. Generate commit: diff2commit generate"
else
    echo "✗ Installation failed. Please install manually:"
    echo "  pip3 install diff2commit"
    exit 1
fi