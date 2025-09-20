#!/bin/bash
# DARKNEXT Quick Start Script

echo "🌐 DARKNEXT - Dark Web Content Monitor"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || venv\Scripts\activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running!"
fi

# Run component test
echo "Testing components..."
python src/main.py --mode test

echo ""
echo "🚀 Setup complete! You can now run:"
echo "   python src/main.py --mode single      # Single scan"
echo "   python src/main.py --mode continuous  # Continuous monitoring"
echo "   python src/main.py --mode stats       # View statistics"
echo ""
echo "⚠️  Make sure Tor is running and .env is configured!"