"""
Tests for HackRX API endpoint.
"""

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_hackrx_endpoint_success(async_client, auth_headers, sample_questions):
    """Test successful HackRX endpoint call."""
    request_data = {
        "documents": "https://example.com/test.pdf",
        "questions": sample_questions
    }
    
    # Mock the query service
    with patch('app.api.v1.dependencies.get_query_service') as mock_service:
        mock_query_service = AsyncMock()
        mock_query_service.process_document_queries.return_value = [
            "Grace period is 30 days.",
            "Waiting period is 36 months.",
            "Yes, maternity is covered after 24 months."
        ]
        mock_service.return_value = mock_query_service
        
        response = await async_client.post(
            "/hackrx/run",
            json=request_data,
            headers=auth_headers
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "answers" in data
    assert len(data["answers"]) == 3

@pytest.mark.asyncio
async def test_hackrx_endpoint_invalid_auth(async_client, sample_questions):
    """Test HackRX endpoint with invalid authentication."""
    request_data = {
        "documents": "https://example.com/test.pdf",
        "questions": sample_questions
    }
    
    response = await async_client.post(
        "/hackrx/run",
        json=request_data,
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_hackrx_endpoint_validation_error(async_client, auth_headers):
    """Test HackRX endpoint with validation errors."""
    # Empty questions
    request_data = {
        "documents": "https://example.com/test.pdf",
        "questions": []
    }
    
    response = await async_client.post(
        "/hackrx/run",
        json=request_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_hackrx_endpoint_processing_error(async_client, auth_headers, sample_questions):
    """Test HackRX endpoint with processing error."""
    request_data = {
        "documents": "https://example.com/test.pdf",
        "questions": sample_questions
    }
    
    # Mock service to raise error
    with patch('app.api.v1.dependencies.get_query_service') as mock_service:
        mock_query_service = AsyncMock()
        mock_query_service.process_document_queries.side_effect = Exception("Processing failed")
        mock_service.return_value = mock_query_service
        
        response = await async_client.post(
            "/hackrx/run",
            json=request_data,
            headers=auth_headers
        )
    
    assert response.status_code == 500
