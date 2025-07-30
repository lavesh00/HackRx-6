"""
Pytest configuration and fixtures.
"""

import asyncio
import os
import tempfile
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment
os.environ['DATABASE_URL'] = 'sqlite:///./test.db'
os.environ['REDIS_ENABLED'] = 'False'
os.environ['DEBUG'] = 'True'

from main import app
from app.api.v1.dependencies import get_query_service, get_document_service
from config.settings import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def settings():
    """Get test settings."""
    return get_settings()

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    # This is a minimal PDF content
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF"""

@pytest.fixture
def sample_questions():
    """Sample questions for testing."""
    return [
        "What is the grace period for premium payment?",
        "What is the waiting period for pre-existing diseases?",
        "Does this policy cover maternity expenses?"
    ]

@pytest.fixture
def auth_headers():
    """Authentication headers for testing."""
    return {
        "Authorization": "Bearer c1be80ee89dc9bdfea91d3a85be77235fdd24ca2063395b84d1b716548a6d9ac"
    }
