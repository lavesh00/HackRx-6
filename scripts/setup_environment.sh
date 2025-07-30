#!/bin/bash

# Setup script for LLM Document Query System
# This script sets up the complete environment for the application

set -e

echo "=== LLM Document Query System Setup ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    print_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

print_status "Detected OS: $OS"

# Update system packages
print_status "Updating system packages..."
if [[ "$OS" == "linux" ]]; then
    sudo apt-get update && sudo apt-get upgrade -y
    sudo apt-get install -y python3.9 python3.9-venv python3.9-dev python3-pip
    sudo apt-get install -y build-essential libmagic1 libmagic-dev
    sudo apt-get install -y curl wget git nginx redis-server
elif [[ "$OS" == "macos" ]]; then
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        print_error "Homebrew not found. Please install Homebrew first."
        exit 1
    fi
    brew update
    brew install python@3.9 libmagic redis nginx
fi

# Check Python version
PYTHON_VERSION=$(python3.9 --version 2>&1 | awk '{print $2}')
print_status "Python version: $PYTHON_VERSION"

# Create project directory
PROJECT_DIR="/opt/llm-query-system"
if [[ ! -d "$PROJECT_DIR" ]]; then
    print_status "Creating project directory: $PROJECT_DIR"
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown $USER:$USER "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3.9 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
print_status "Creating application directories..."
mkdir -p data/{embeddings,processed_docs,cache}
mkdir -p logs
mkdir -p /var/log/llm-query-system

# Set permissions
sudo chown -R $USER:$USER "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"

# Create environment file from template
if [[ ! -f .env ]]; then
    print_status "Creating environment configuration..."
    cp .env.example .env
    print_warning "Please edit .env file with your configuration (especially GOOGLE_API_KEY)"
fi

# Setup systemd service
print_status "Setting up systemd service..."
sudo tee /etc/systemd/system/llm-query-system.service > /dev/null <<EOF
[Unit]
Description=LLM Document Query System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup nginx configuration
print_status "Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/llm-query-system > /dev/null <<EOF
server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/llm-query-system /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/llm-query-system > /dev/null <<EOF
/var/log/llm-query-system/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Configure Redis
print_status "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable llm-query-system
sudo systemctl enable nginx

# Initialize database
print_status "Initializing database..."
python -c "
import asyncio
from app.database.connection import init_database
asyncio.run(init_database())
"

# Test the setup
print_status "Testing the setup..."
python -c "
import sys
try:
    from app.core.embedding_engine import EmbeddingEngine
    from app.core.llm_client import LLMClient
    print('✓ Core modules imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"

print_status "Setup completed successfully!"
print_warning "Next steps:"
echo "1. Edit .env file with your Google API key and other settings"
echo "2. Start the service: sudo systemctl start llm-query-system"
echo "3. Check status: sudo systemctl status llm-query-system"
echo "4. View logs: sudo journalctl -u llm-query-system -f"
echo "5. Test API: curl http://localhost/health"

print_status "Setup script finished."
