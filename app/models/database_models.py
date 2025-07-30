"""
Database models for SQLAlchemy ORM.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Document(Base):
    """Document metadata model."""
    
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    title = Column(String)
    size_bytes = Column(Integer)
    hash_md5 = Column(String, index=True)
    
    # Processing metadata
    status = Column(String, default="pending")
    chunks_count = Column(Integer, default=0)
    embeddings_count = Column(Integer, default=0)
    processing_time_ms = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Additional metadata
    metadata = Column(JSON, default=dict)

class DocumentChunk(Base):
    """Document chunk model for text segments."""
    
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    
    # Positioning information
    start_char = Column(Integer)
    end_char = Column(Integer)
    page_number = Column(Integer)
    
    # Embedding information
    embedding_vector = Column(JSON)  # Store as JSON array
    embedding_model = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    metadata = Column(JSON, default=dict)

class QueryLog(Base):
    """Query processing log model."""
    
    __tablename__ = "query_logs"
    
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    query_text = Column(Text, nullable=False)
    answer = Column(Text)
    
    # Performance metrics
    processing_time_ms = Column(Float)
    chunks_retrieved = Column(Integer)
    confidence_score = Column(Float)
    
    # LLM usage
    tokens_used = Column(Integer)
    model_used = Column(String)
    
    # Client information
    client_ip = Column(String)
    user_agent = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional data
    metadata = Column(JSON, default=dict)

class SystemMetrics(Base):
    """System performance metrics model."""
    
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    
    # Categorization
    metric_type = Column(String, nullable=False)  # performance, usage, error
    component = Column(String)  # embedding, llm, storage, etc.
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional context
    metadata = Column(JSON, default=dict)

class CacheEntry(Base):
    """Cache entries for query results."""
    
    __tablename__ = "cache_entries"
    
    id = Column(String, primary_key=True, index=True)
    cache_key = Column(String, nullable=False, index=True, unique=True)
    cache_value = Column(JSON, nullable=False)
    
    # Cache metadata
    cache_type = Column(String, nullable=False)  # embedding, query, document
    ttl_seconds = Column(Integer)
    hit_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    # Size tracking
    size_bytes = Column(Integer)
