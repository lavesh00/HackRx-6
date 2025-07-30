"""
Embedding generation and FAISS vector search engine.
"""

import asyncio
import logging
import os
import pickle
from typing import Dict, List, Optional, Tuple, Union

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.utils.exceptions import EmbeddingGenerationError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """Handles text embedding generation and vector similarity search."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", cache_dir: Optional[str] = None):
        self.settings = get_settings()
        self.model_name = model_name
        self.cache_dir = cache_dir or self.settings.EMBEDDINGS_DIR
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.chunk_metadata: Dict[int, Dict] = {}
        self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
        
        # Initialize directories
        os.makedirs(self.cache_dir, exist_ok=True)
        
    async def initialize(self):
        """Initialize the embedding model and FAISS index."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        try:
            logger.info(f"Initializing embedding engine with model: {self.model_name}")
            
            # Load embedding model
            await self._load_model()
            
            # Initialize or load FAISS index
            await self._initialize_index()
            
            logger.info("Embedding engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding engine: {e}")
            raise EmbeddingGenerationError(f"Initialization failed: {str(e)}")
    
    async def _load_model(self):
        """Load the sentence transformer model."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(self.model_name, cache_folder=self.cache_dir)
            )
            
            # Verify model dimension
            test_embedding = await self.encode(["test"], batch_size=1)
            actual_dim = test_embedding.shape[1]
            if actual_dim != self.dimension:
                self.dimension = actual_dim
                logger.info(f"Updated embedding dimension to: {self.dimension}")
                
        except Exception as e:
            raise EmbeddingGenerationError(f"Failed to load model: {str(e)}")
    
    async def _initialize_index(self):
        """Initialize or load existing FAISS index."""
        index_path = os.path.join(self.cache_dir, "faiss_index.bin")
        metadata_path = os.path.join(self.cache_dir, "chunk_metadata.pkl")
        
        try:
            if os.path.exists(index_path) and os.path.exists(metadata_path):
                # Load existing index
                logger.info("Loading existing FAISS index")
                self.index = faiss.read_index(index_path)
                
                with open(metadata_path, 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
                
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
            else:
                # Create new index
                logger.info("Creating new FAISS index")
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product for cosine similarity
                self.chunk_metadata = {}
                
        except Exception as e:
            logger.warning(f"Failed to load existing index: {e}, creating new one")
            self.index = faiss.IndexFlatIP(self.dimension)
            self.chunk_metadata = {}
    
    async def encode(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of embeddings
        """
        if not self.model:
            await self.initialize()
        
        if not texts:
            return np.array([])
        
        try:
            batch_size = batch_size or self.settings.EMBEDDING_BATCH_SIZE
            
            # Process in batches to manage memory
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Run encoding in thread pool
                loop = asyncio.get_event_loop()
                batch_embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.model.encode(
                        batch_texts,
                        convert_to_numpy=True,
                        normalize_embeddings=True  # For cosine similarity
                    )
                )
                
                all_embeddings.append(batch_embeddings)
                
                # Log progress for large batches
                if len(texts) > 100:
                    logger.info(f"Encoded {min(i + batch_size, len(texts))}/{len(texts)} texts")
            
            embeddings = np.vstack(all_embeddings)
            logger.info(f"Generated {embeddings.shape[0]} embeddings")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingGenerationError(f"Failed to generate embeddings: {str(e)}")
    
    async def add_documents(self, document_id: str, chunks: List[str], metadata: Optional[Dict] = None) -> None:
        """
        Add document chunks to the vector index.
        
        Args:
            document_id: Unique document identifier
            chunks: List of text chunks
            metadata: Additional metadata for the document
        """
        if not self.model or not self.index:
            await self.initialize()
        
        try:
            logger.info(f"Adding {len(chunks)} chunks for document {document_id}")
            
            # Generate embeddings
            embeddings = await self.encode(chunks)
            
            # Get current index size for IDs
            start_id = self.index.ntotal
            
            # Add embeddings to index
            self.index.add(embeddings.astype(np.float32))
            
            # Store metadata
            for i, chunk in enumerate(chunks):
                chunk_id = start_id + i
                self.chunk_metadata[chunk_id] = {
                    'document_id': document_id,
                    'chunk_index': i,
                    'text': chunk,
                    'metadata': metadata or {}
                }
            
            # Save index and metadata
            await self._save_index()
            
            logger.info(f"Successfully added {len(chunks)} chunks to index")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise EmbeddingGenerationError(f"Failed to add documents: {str(e)}")
    
    async def search(self, query: str, k: int = 8, threshold: float = 0.3) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query: Query text
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar chunks with metadata
        """
        if not self.model or not self.index:
            await self.initialize()
        
        if self.index.ntotal == 0:
            logger.warning("Index is empty, no results to return")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.encode([query])
            
            # Search in index
            scores, indices = self.index.search(query_embedding.astype(np.float32), k)
            
            # Filter results by threshold and format output
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                    
                if score >= threshold:
                    chunk_info = self.chunk_metadata.get(idx, {})
                    results.append({
                        'chunk_id': int(idx),
                        'score': float(score),
                        'text': chunk_info.get('text', ''),
                        'document_id': chunk_info.get('document_id', ''),
                        'chunk_index': chunk_info.get('chunk_index', 0),
                        'metadata': chunk_info.get('metadata', {})
                    })
            
            logger.info(f"Found {len(results)} relevant chunks for query")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise EmbeddingGenerationError(f"Search failed: {str(e)}")
    
    async def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            index_path = os.path.join(self.cache_dir, "faiss_index.bin")
            metadata_path = os.path.join(self.cache_dir, "chunk_metadata.pkl")
            
            # Save index
            faiss.write_index(self.index, index_path)
            
            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.chunk_metadata, f)
            
            logger.debug("Index and metadata saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    async def get_index_stats(self) -> Dict:
        """Get statistics about the current index."""
        if not self.index:
            await self.initialize()
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'model_name': self.model_name,
            'unique_documents': len(set(
                meta.get('document_id', '') for meta in self.chunk_metadata.values()
            )) if self.chunk_metadata else 0
        }
    
    async def clear_document(self, document_id: str) -> None:
        """Remove all chunks for a specific document."""
        if not self.index:
            await self.initialize()
        
        # Find chunks to remove
        chunks_to_remove = [
            chunk_id for chunk_id, meta in self.chunk_metadata.items()
            if meta.get('document_id') == document_id
        ]
        
        if not chunks_to_remove:
            logger.warning(f"No chunks found for document {document_id}")
            return
        
        # FAISS doesn't support removal, so we need to rebuild the index
        logger.info(f"Rebuilding index after removing {len(chunks_to_remove)} chunks")
        
        # Get all remaining embeddings and metadata
        remaining_embeddings = []
        new_metadata = {}
        new_id = 0
        
        for chunk_id in range(self.index.ntotal):
            if chunk_id not in chunks_to_remove:
                # Get embedding
                embedding = self.index.reconstruct(chunk_id)
                remaining_embeddings.append(embedding)
                
                # Update metadata with new ID
                old_meta = self.chunk_metadata.get(chunk_id, {})
                new_metadata[new_id] = old_meta
                new_id += 1
        
        # Create new index
        self.index = faiss.IndexFlatIP(self.dimension)
        if remaining_embeddings:
            embeddings_array = np.vstack(remaining_embeddings)
            self.index.add(embeddings_array)
        
        self.chunk_metadata = new_metadata
        
        # Save updated index
        await self._save_index()
        
        logger.info(f"Removed {len(chunks_to_remove)} chunks for document {document_id}")
