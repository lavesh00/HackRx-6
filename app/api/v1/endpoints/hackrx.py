"""
HackRX API endpoint for document query processing.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.v1.dependencies import get_query_service
from app.models.request_models import HackRXRequest
from app.models.response_models import HackRXResponse
from app.services.query_service import QueryService
from app.utils.exceptions import (
    DocumentProcessingError,
    EmbeddingGenerationError,
    LLMProcessingError,
    ValidationError
)
from config.settings import get_settings
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
settings = get_settings()

async def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify bearer token authentication."""
    if credentials.credentials != settings.BEARER_TOKEN:
        logger.warning(f"Invalid bearer token attempted: {credentials.credentials[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@router.post("/hackrx/run", response_model=HackRXResponse)
async def process_hackrx_query(
    request: HackRXRequest,
    query_service: QueryService = Depends(get_query_service),
    token: str = Depends(verify_bearer_token)
) -> HackRXResponse:
    """
    Process document queries using LLM and vector search.
    
    Args:
        request: HackRX request with documents URL and questions
        query_service: Query processing service
        token: Verified bearer token
    
    Returns:
        HackRXResponse with answers array
    
    Raises:
        HTTPException: For various processing errors
    """
    logger.info(f"Processing HackRX request with {len(request.questions)} questions")
    
    try:
        # Validate request
        if not request.documents:
            raise ValidationError("Documents URL is required")
        
        if not request.questions:
            raise ValidationError("At least one question is required")
        
        if len(request.questions) > 20:
            raise ValidationError("Maximum 20 questions allowed per request")
        
        # Process the request
        answers = await query_service.process_document_queries(
            documents_url=request.documents,
            questions=request.questions
        )
        
        logger.info(f"Successfully processed {len(answers)} questions")
        return HackRXResponse(answers=answers)
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process document: {str(e)}"
        )
    
    except EmbeddingGenerationError as e:
        logger.error(f"Embedding generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings"
        )
    
    except LLMProcessingError as e:
        logger.error(f"LLM processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service temporarily unavailable"
        )
    
    except asyncio.TimeoutError:
        logger.error("Request timeout")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request processing timeout"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
