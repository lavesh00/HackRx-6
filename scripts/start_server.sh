#!/bin/bash

# Start script for LLM Document Query System

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    print_error "Virtual environment not found. Run setup_environment.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    print_error ".env file not found. Copy .env.example to .env and configure it."
    exit 1
fi

# Check required directories
print_status "Checking directories..."
mkdir -p data/{embeddings,processed_docs,cache}
mkdir -p logs

# Check dependencies
print_status "Checking dependencies..."
python -c "
import sys
required_modules = [
    'fastapi', 'uvicorn', 'sentence_transformers', 
    'faiss', 'google.generativeai', 'PyPDF2'
]
missing = []
for module in required_modules:
    try:
        __import__(module.split('.')[0])
    except ImportError:
        missing.append(module)

if missing:
    print(f'Missing modules: {missing}')
    print('Run: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('✓ All dependencies available')
"

# Check Google API key
print_status "Checking Google API key..."
if ! grep -q "GOOGLE_API_KEY=" .env || grep -q "GOOGLE_API_KEY=your_google_api_key_here" .env; then
    print_warning "Google API key not configured in .env file"
    print_warning "The system will still start but LLM functionality will not work"
fi

# Start the server
print_status "Starting LLM Document Query System..."

# Development mode
if [[ "$1" == "--dev" ]]; then
    print_status "Starting in development mode..."
    export DEBUG=True
    python main.py
# Production mode with gunicorn
elif [[ "$1" == "--prod" ]]; then
    print_status "Starting in production mode..."
    if ! command -v gunicorn &> /dev/null; then
        print_error "Gunicorn not found. Install with: pip install gunicorn"
        exit 1
    fi
    gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
# Default mode
else
    print_status "Starting in default mode..."
    python main.py
fi
