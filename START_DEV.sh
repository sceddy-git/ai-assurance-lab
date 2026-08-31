#!/bin/bash

echo "🚀 Starting AI Assurance Lab Development Server"
echo "=============================================="
echo ""

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Activate venv
source venv/bin/activate

echo "✅ Virtual environment activated"
echo ""
echo "Environment loaded:"
echo "  - Flask: 3.0.0"
echo "  - Boto3: 1.28.0 (AWS SDK)"
echo "  - Cryptography: 41.0.0"
echo "  - All dependencies installed"
echo ""

# Check for .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Copy .env.example to .env and configure with your Cognito credentials"
    exit 1
fi

echo "✅ .env file found"
echo ""
echo "Starting Flask development server..."
echo "📍 Visit: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=============================================="
echo ""

python3 app.py
