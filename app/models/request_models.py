"""
Request models for API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Union
import re

class HackRXRequest(BaseModel):
    """Request model for HackRX endpoint."""
    
    documents: str = Field(
        ...,
        description="URL to document (PDF, DOCX, or email)",
        min_length=1,
        max_length=2048
    )
    
    questions: List[str] = Field(
        ...,
        description="List of questions to answer about the document",
        min_items=1,
        max_items=20
    )
    
    @validator("documents")
    def validate_documents_url(cls, v: str) -> str:
        """Validate document URL format."""
        if not v.strip():
            raise ValueError("Document URL cannot be empty")
        
        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError("Invalid URL format")
        
        return v
    
    @validator("questions")
    def validate_questions(cls, v: List[str]) -> List[str]:
        """Validate questions list."""
        if not v:
            raise ValueError("At least one question is required")
        
        validated_questions = []
        for i, question in enumerate(v):
            if not question or not question.strip():
                raise ValueError(f"Question {i+1} cannot be empty")
            
            question = question.strip()
            if len(question) < 3:
                raise ValueError(f"Question {i+1} is too short (minimum 3 characters)")
            
            if len(question) > 500:
                raise ValueError(f"Question {i+1} is too long (maximum 500 characters)")
            
            validated_questions.append(question)
        
        return validated_questions
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": "https://example.com/policy.pdf",
                "questions": [
                    "What is the grace period for premium payment?",
                    "What is the waiting period for pre-existing diseases?"
                ]
            }
        }

class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    
    file_url: str = Field(
        ...,
        description="URL to the document file",
        min_length=1,
        max_length=2048
    )
    
    document_type: str = Field(
        default="auto",
        description="Document type (pdf, docx, email, or auto-detect)"
    )
    
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata for the document"
    )
    
    @validator("document_type")
    def validate_document_type(cls, v: str) -> str:
        """Validate document type."""
        allowed_types = ["pdf", "docx", "email", "auto"]
        if v.lower() not in allowed_types:
            raise ValueError(f"Document type must be one of: {allowed_types}")
        return v.lower()

class QueryRequest(BaseModel):
    """Request model for single query processing."""
    
    query: str = Field(
        ...,
        description="Query text to process",
        min_length=3,
        max_length=500
    )
    
    document_id: str = Field(
        ...,
        description="ID of the document to query against"
    )
    
    context_limit: int = Field(
        default=5,
        description="Maximum number of context chunks to retrieve",
        ge=1,
        le=20
    )
    
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity threshold for context retrieval",
        ge=0.0,
        le=1.0
    )
