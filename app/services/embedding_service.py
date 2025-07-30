"""
Embedding service for managing vector embeddings and search operations.
"""

import logging
from typing import Dict, List, Optional

from app.core.embedding_engine import EmbeddingEngine
from app.services.cache_service import CacheService
from app.utils.exceptions import EmbeddingGenerationError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for embedding operations."""
    
    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        cache_service: Optional[CacheService] = None
    ):
        self.embedding_engine = embedding_engine
        self.cache_service = cache_service
        self.settings = get_settings()
    
    async def add_document_embeddings(
        self,
        document_id: str,
        chunks: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add document embeddings to the vector index.
        
        Args:
            document_id: Unique document identifier
            chunks: List of text chunks
            metadata: Additional metadata
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Adding embeddings for document {document_id} ({len(chunks)} chunks)")
            
            # Add to embedding engine
            await self.embedding_engine.add_documents(
                document_id=document_id,
                chunks=chunks,
                metadata=metadata
            )
            
            # Update cache if available
            if self.cache_service:
                cache_key = f"embeddings:{document_id}"
                embedding_info = {
                    'document_id': document_id,
                    'chunks_count': len(chunks),
                    'metadata': metadata or {},
                    'timestamp': self._get_timestamp()
                }
                await self.cache_service.set(cache_key, embedding_info, ttl=7200)
            
            return {
                'document_id': document_id,
                'chunks_processed': len(chunks),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to add document embeddings: {e}")
            raise EmbeddingGenerationError(f"Embedding service failed: {str(e)}")
    
    async def search_similar_chunks(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar chunks in the vector index.
        
        Args:
            query: Search query
            k: Number of results to return
            threshold: Minimum similarity threshold
            document_id: Optional document ID filter
            
        Returns:
            List of similar chunks
        """
        try:
            # Generate cache key
            cache_key = f"search:{hash(query)}:{k}:{threshold}:{document_id or 'all'}"
            
            # Check cache first
            if self.cache_service:
                cached_results = await self.cache_service.get(cache_key)
                if cached_results:
                    logger.info("Retrieved search results from cache")
                    return cached_results
            
            # Perform search
            results = await self.embedding_engine.search(
                query=query,
                k=k,
                threshold=threshold
            )
            
            # Filter by document_id if specified
            if document_id:
                results = [r for r in results if r.get('document_id') == document_id]
            
            # Cache results
            if self.cache_service:
                await self.cache_service.set(cache_key, results, ttl=300)  # 5 minutes
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise EmbeddingGenerationError(f"Search service failed: {str(e)}")
    
    async def get_embedding_stats(self) -> Dict:
        """Get embedding engine statistics."""
        try:
            return await self.embedding_engine.get_index_stats()
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {}
    
    async def remove_document_embeddings(self, document_id: str) -> bool:
        """Remove embeddings for a specific document."""
        try:
            await self.embedding_engine.clear_document(document_id)
            
            # Clear cache
            if self.cache_service:
                cache_key = f"embeddings:{document_id}"
                await self.cache_service.delete(cache_key)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove document embeddings: {e}")
            return False
    
    def _get_timestamp(self) -> int:
        """Get current timestamp."""
        import time
        return int(time.time())
