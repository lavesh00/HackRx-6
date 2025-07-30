"""
Document service for managing document processing and storage.
"""

import logging
import uuid
from typing import Dict, List, Optional

from app.core.document_processor import DocumentProcessor
from app.services.cache_service import CacheService
from app.utils.exceptions import DocumentProcessingError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for document management operations."""
    
    def __init__(
        self, 
        document_processor: DocumentProcessor,
        cache_service: Optional[CacheService] = None
    ):
        self.document_processor = document_processor
        self.cache_service = cache_service
        self.settings = get_settings()
    
    async def process_document(
        self, 
        document_url: str,
        force_reprocess: bool = False
    ) -> Dict:
        """
        Process a document with caching support.
        
        Args:
            document_url: URL to the document
            force_reprocess: Whether to force reprocessing even if cached
            
        Returns:
            Dictionary containing processed document data
        """
        try:
            cache_key = f"doc_service:{hash(document_url)}"
            
            # Check cache first (unless forced reprocessing)
            if not force_reprocess and self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    logger.info("Retrieved processed document from cache")
                    return cached_result
            
            # Process document
            logger.info(f"Processing document: {document_url}")
            result = await self.document_processor.process_document_from_url(document_url)
            
            # Add service-level metadata
            result['service_metadata'] = {
                'processing_timestamp': self._get_timestamp(),
                'service_version': '1.0.0',
                'cached': False
            }
            
            # Cache result
            if self.cache_service:
                await self.cache_service.set(cache_key, result, ttl=3600)
            
            return result
            
        except Exception as e:
            logger.error(f"Document service processing failed: {e}")
            raise DocumentProcessingError(f"Service processing failed: {str(e)}")
    
    async def get_document_metadata(self, document_url: str) -> Optional[Dict]:
        """Get metadata for a processed document."""
        try:
            cache_key = f"doc_service:{hash(document_url)}"
            
            if self.cache_service:
                cached_doc = await self.cache_service.get(cache_key)
                if cached_doc:
                    return cached_doc.get('metadata', {})
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document metadata: {e}")
            return None
    
    async def validate_document_url(self, document_url: str) -> bool:
        """Validate if a document URL is accessible and processable."""
        try:
            # This would typically involve a HEAD request to check accessibility
            # For now, we'll do basic URL validation
            from urllib.parse import urlparse
            
            parsed = urlparse(document_url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Could add more sophisticated validation here
            return True
            
        except Exception:
            return False
    
    def _get_timestamp(self) -> int:
        """Get current timestamp."""
        import time
        return int(time.time())
