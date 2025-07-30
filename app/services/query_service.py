"""
Query service for handling document queries and answer generation.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional

from app.core.query_processor import QueryProcessor
from app.services.cache_service import CacheService
from app.utils.exceptions import QueryProcessingError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class QueryService:
    """Service for query processing operations."""
    
    def __init__(
        self,
        query_processor: QueryProcessor,
        cache_service: Optional[CacheService] = None
    ):
        self.query_processor = query_processor
        self.cache_service = cache_service
        self.settings = get_settings()
    
    async def process_document_queries(
        self,
        documents_url: str,
        questions: List[str]
    ) -> List[str]:
        """
        Process multiple queries against a document.
        
        Args:
            documents_url: URL to the document
            questions: List of questions to answer
            
        Returns:
            List of answers
        """
        start_time = time.time()
        session_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Query service processing {len(questions)} questions (Session: {session_id})")
            
            # Validate inputs
            self._validate_query_request(documents_url, questions)
            
            # Process through query processor
            answers = await self.query_processor.process_document_queries(
                documents_url=documents_url,
                questions=questions
            )
            
            # Log session metrics
            processing_time = (time.time() - start_time) * 1000
            await self._log_session_metrics(session_id, len(questions), processing_time)
            
            return answers
            
        except Exception as e:
            logger.error(f"Query service processing failed (Session: {session_id}): {e}")
            raise QueryProcessingError(f"Query service failed: {str(e)}")
    
    async def process_single_query(
        self,
        documents_url: str,
        question: str
    ) -> str:
        """
        Process a single query against a document.
        
        Args:
            documents_url: URL to the document
            question: Question to answer
            
        Returns:
            Generated answer
        """
        try:
            answers = await self.process_document_queries(
                documents_url=documents_url,
                questions=[question]
            )
            return answers[0] if answers else "No answer generated."
            
        except Exception as e:
            logger.error(f"Single query processing failed: {e}")
            raise QueryProcessingError(f"Single query failed: {str(e)}")
    
    def _validate_query_request(self, documents_url: str, questions: List[str]) -> None:
        """Validate query request parameters."""
        if not documents_url or not documents_url.strip():
            raise QueryProcessingError("Document URL is required")
        
        if not questions:
            raise QueryProcessingError("At least one question is required")
        
        if len(questions) > 20:
            raise QueryProcessingError("Maximum 20 questions allowed per request")
        
        for i, question in enumerate(questions):
            if not question or not question.strip():
                raise QueryProcessingError(f"Question {i+1} cannot be empty")
            
            if len(question.strip()) < 3:
                raise QueryProcessingError(f"Question {i+1} is too short")
            
            if len(question) > 500:
                raise QueryProcessingError(f"Question {i+1} is too long (max 500 characters)")
    
    async def _log_session_metrics(
        self,
        session_id: str,
        question_count: int,
        processing_time_ms: float
    ) -> None:
        """Log session metrics for monitoring."""
        try:
            metrics = {
                'session_id': session_id,
                'question_count': question_count,
                'processing_time_ms': processing_time_ms,
                'avg_time_per_question': processing_time_ms / question_count,
                'timestamp': int(time.time())
            }
            
            # Store in cache for analytics
            if self.cache_service:
                cache_key = f"metrics:session:{session_id}"
                await self.cache_service.set(cache_key, metrics, ttl=86400)  # 24 hours
            
            logger.info(f"Session metrics: {metrics}")
            
        except Exception as e:
            logger.warning(f"Failed to log session metrics: {e}")
    
    async def get_service_health(self) -> Dict:
        """Get service health status."""
        try:
            processor_stats = await self.query_processor.get_processing_stats()
            
            return {
                'status': 'healthy',
                'processor_stats': processor_stats,
                'cache_enabled': self.cache_service is not None,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': int(time.time())
            }
