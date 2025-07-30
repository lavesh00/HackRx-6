# LLM-Powered Intelligent Query-Retrieval System

A production-ready document query system that processes PDFs, DOCX, and email documents to answer contextual queries using Google Gemini API and FAISS vector search.

## Features

- **Document Processing**: Support for PDF, DOCX, and email documents
- **Semantic Search**: FAISS-based vector search with sentence transformers
- **LLM Integration**: Google Gemini Pro API for intelligent query processing
- **Memory Optimized**: Designed for 8GB RAM and i5 processor constraints
- **Real-time Processing**: Sub-5-second response times
- **Production Ready**: Docker deployment with comprehensive error handling

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your settings
3. Run `chmod +x scripts/setup_environment.sh && scripts/setup_environment.sh`
4. Start with Docker: `docker-compose up -d`

## API Usage

curl -X POST "http://localhost:8000/hackrx/run"
-H "Authorization: Bearer c1be80ee89dc9bdfea91d3a85be77235fdd24ca2063395b84d1b716548a6d9ac"
-H "Content-Type: application/json"
-d '{
"documents": "https://example.com/document.pdf",
"questions": ["What is the coverage limit?"]
}'

## Architecture

- **Backend**: FastAPI with async processing
- **LLM**: Google Gemini Pro (Free tier)
- **Vector DB**: FAISS (Local, memory-efficient)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **Database**: SQLite for metadata
- **Deployment**: Docker + Docker Compose

## System Requirements

- RAM: 8GB minimum
- CPU: i5 processor or equivalent
- Storage: 10GB free space
- Network: Stable internet connection

## Documentation

- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Server Setup](docs/SERVER_SETUP.md)