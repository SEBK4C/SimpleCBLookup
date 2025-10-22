#!/bin/bash

set -e  # Exit on error

echo ""
echo "================================================================================"
echo "  SimpleCBLookup Setup"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  - Install UV (fast Python package manager) if needed"
echo "  - Install dependencies"
echo "  - Run setup.py (which will prompt for API key and data options)"
echo ""
echo "Note: If you have existing data, you'll be prompted to use it or download fresh."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add cargo bin to PATH
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
    
    # Try to find uv in common locations
    if [ -f "$HOME/.cargo/bin/uv" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    elif [ -f "$HOME/.local/bin/uv" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

echo "✓ UV is ready"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies using UV
echo "Installing dependencies..."
uv pip install httpx typer rich duckdb

echo ""
echo "✓ Dependencies installed"
echo ""

# Run the setup script
echo "Running setup..."
python setup.py

