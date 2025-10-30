#!/usr/bin/env bash
# Quick start script using uv

set -e

echo "========================================="
echo "  AI Trading Bot - UV Quick Start"
echo "========================================="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo ""
    echo "Install uv:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    exit 1
fi

echo "✅ uv is installed"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies using uv (much faster than pip)
echo "📥 Installing dependencies with uv..."
uv pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the bot:"
echo "  python main.py"
echo ""
echo "Or use uv run (no need to activate venv):"
echo "  uv run python main.py"
echo ""

