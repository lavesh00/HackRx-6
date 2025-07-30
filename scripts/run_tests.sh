#!/bin/bash

# Test runner script for LLM Document Query System

set -e

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

# Get project directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -d "venv" ]]; then
    source venv/bin/activate
else
    print_error "Virtual environment not found"
    exit 1
fi

# Install test dependencies if not present
print_status "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-cov httpx

# Create test database
export DATABASE_URL="sqlite:///./test.db"
export REDIS_ENABLED="False"

# Run linting
print_status "Running code quality checks..."
if command -v flake8 &> /dev/null; then
    print_status "Running flake8..."
    flake8 app/ --max-line-length=120 --ignore=E203,W503 || print_warning "Flake8 found issues"
fi

if command -v black &> /dev/null; then
    print_status "Checking code formatting with black..."
    black --check app/ || print_warning "Code formatting issues found"
fi

if command -v mypy &> /dev/null; then
    print_status "Running type checking with mypy..."
    mypy app/ || print_warning "Type checking issues found"
fi

# Run tests
print_status "Running tests..."

# Unit tests
print_status "Running unit tests..."
pytest tests/ -v --tb=short

# Integration tests
print_status "Running integration tests..."
pytest tests/test_api/ -v --tb=short

# Performance tests
if [[ "$1" == "--performance" ]]; then
    print_status "Running performance tests..."
    pytest tests/test_performance/ -v --tb=short
fi

# Coverage report
if [[ "$1" == "--coverage" ]]; then
    print_status "Generating coverage report..."
    pytest tests/ --cov=app --cov-report=html --cov-report=term
    print_status "Coverage report generated in htmlcov/"
fi

# Cleanup
rm -f test.db

print_status "Test run completed!"
