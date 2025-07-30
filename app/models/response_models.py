"""
Response models for API endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class HackRXResponse(BaseModel):
    """Response model for HackRX endpoint."""
    
    answers: List[str] = Field(
        ...,
        description="List of answers corresponding to the input questions"
    )
    
    class Config:
        json_schema_extra = {  # ✅ Fixed: was schema_extra
            "example": {
                "answers": [
                    "A grace period of thirty days is provided for premium payment after the due date.",
                    "There is a waiting period of thirty-six (36) months for pre-existing diseases."
                ]
            }
        }

class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(
        ...,
        description="Overall system status",
        pattern="^(healthy|degraded|unhealthy)$"  # ✅ Fixed: was regex=
    )
    
    timestamp: int = Field(
        ...,
        description="Unix timestamp of the health check"
    )
    
    response_time_ms: float = Field(
        ...,
        description="Response time in milliseconds"
    )
    
    components: Dict[str, bool] = Field(
        ...,
        description="Status of individual system components"
    )
    
    version: str = Field(
        ...,
        description="Application version"
    )
    
    class Config:
        json_schema_extra = {  # ✅ Fixed: was schema_extra
            "example": {
                "status": "healthy",
                "timestamp": 1700000000,
                "response_time_ms": 45.2,
                "components": {
                    "api": True,
                    "database": True,
                    "embeddings": True,
                    "llm": True,
                    "storage": True
                },
                "version": "1.0.0"
            }
        }

class DocumentProcessingResponse(BaseModel):
    """Response model for document processing."""
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the processed document"
    )
    
    status: str = Field(
        ...,
        description="Processing status"
    )
    
    chunks_created: int = Field(
        ...,
        description="Number of text chunks created"
    )
    
    embeddings_generated: int = Field(
        ...,
        description="Number of embeddings generated"
    )
    
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metadata"
    )

class QueryResponse(BaseModel):
    """Response model for query processing."""
    
    answer: str = Field(
        ...,
        description="Generated answer to the query"
    )
    
    confidence: float = Field(
        ...,
        description="Confidence score for the answer",
        ge=0.0,
        le=1.0
    )
    
    sources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Source chunks used to generate the answer"
    )
    
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )

class ErrorResponse(BaseModel):
    """Response model for error cases."""
    
    error: str = Field(
        ...,
        description="Error type or code"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    details: Optional[str] = Field(
        None,
        description="Additional error details"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    
    request_id: Optional[str] = Field(
        None,
        description="Request identifier for tracking"
    )
