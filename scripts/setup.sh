#!/bin/bash
# Setup script for AI Billing Agent

set -e

echo "🚀 Setting up AI Billing Agent..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "✏️  Please edit .env with your API credentials"
fi

# Create logs directory
mkdir -p logs

# Initialize database
echo "🗄️  Initializing database..."
alembic upgrade head || echo "⚠️  Database migration failed - will create tables on first run"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API credentials"
echo "  2. Start services:"
echo "     - API:          uvicorn api.main:app --reload"
echo "     - Celery:       celery -A tasks.celery_app worker --loglevel=info"
echo "     - Celery Beat:  celery -A tasks.celery_app beat --loglevel=info"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
echo "📖 View API docs at: http://localhost:8000/docs"

