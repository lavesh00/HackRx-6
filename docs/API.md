# API Documentation

## Overview

The LLM Document Query System provides a RESTful API for processing documents and answering questions using advanced language models and vector search.

## Authentication

All API endpoints require Bearer token authentication:

Authorization: Bearer c1be80ee89dc9bdfea91d3a85be77235fdd24ca2063395b84d1b716548a6d9ac

## Endpoints

### POST /hackrx/run

Process document queries and generate answers.

**Request:**
{
"documents": "https://example.com/document.pdf",
"questions": [
"What is the grace period?",
"What are the coverage limits?"
]
}

**Response:**
{
"answers": [
"The grace period is 30 days for premium payment.",
"Coverage limits vary by plan type and are detailed in the benefits table."
]
}

**Status Codes:**
- 200: Success
- 400: Bad Request (validation error)
- 401: Unauthorized
- 422: Unprocessable Entity (document processing error)
- 500: Internal Server Error
- 503: Service Unavailable (LLM quota exceeded)

### GET /health

System health check endpoint.

**Response:**
{
"status": "healthy",
"timestamp": 1700000000,
"response_time_ms": 45.2,
"components": {
"api": true,
"database": true,
"embeddings": true,
"llm": true,
"storage": true
},
"version": "1.0.0"
}

## Rate Limiting

The API implements rate limiting:
- 60 requests per minute per IP address
- Google Gemini: 15 requests per minute
- 1M tokens per day limit

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Requests per minute limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time

## Error Handling

All errors return a consistent format:

{
"detail": "Error description",
"error_code": "ERROR_TYPE",
"timestamp": "2023-11-15T10:30:00Z"
}

