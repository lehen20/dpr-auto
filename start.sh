#!/bin/bash

# Production-grade startup script for Document Search Assistant

echo "🚀 Starting Document Search Assistant..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure your GOOGLE_API_KEY"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create uploads directory
mkdir -p uploads

echo "✅ Setup complete!"
echo ""
echo "🔹 To start the application:"
echo "   1. Backend:  python run_backend.py"
echo "   2. Frontend: python run_frontend.py"
echo ""
echo "🔹 Or run both in separate terminals after activating the virtual environment:"
echo "   source venv/bin/activate"