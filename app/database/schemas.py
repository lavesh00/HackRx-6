"""
Database schema definitions using SQLAlchemy.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Index
from sqlalchemy.sql import func
from app.database.connection import Base

class DocumentRecord(Base):
    """Document processing record."""
    
    __tablename__ = "documents"
    
    id = Column(String(64), primary_key=True)  # MD5 hash
    url = Column(String(2048), nullable=False)
    file_type = Column(String(50), nullable=False)
    title = Column(String(500))
    size_bytes = Column(Integer)
    
    # Processing status
    status = Column(String(20), default="pending", index=True)
    chunks_count = Column(Integer, default=0)
    embeddings_count = Column(Integer, default=0)
    processing_time_ms = Column(Float)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_documents_status_created', 'status', 'created_at'),
        Index('idx_documents_url_hash', 'url'),
    )

class QueryRecord(Base):
    """Query processing record."""
    
    __tablename__ = "queries"
    
    id = Column(String(36), primary_key=True)  # UUID
    document_id = Column(String(64), index=True)
    query_text = Column(Text, nullable=False)
    answer = Column(Text)
    
    # Performance metrics
    processing_time_ms = Column(Float)
    chunks_retrieved = Column(Integer)
    confidence_score = Column(Float)
    
    # LLM usage
    tokens_used = Column(Integer)
    model_used = Column(String(100))
    
    # Request info
    client_ip = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    session_id = Column(String(36), index=True)
    
    # Status
    status = Column(String(20), default="completed", index=True)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional data
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_queries_document_created', 'document_id', 'created_at'),
        Index('idx_queries_session_created', 'session_id', 'created_at'),
    )

class MetricsRecord(Base):
    """System metrics record."""
    
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50), nullable=False, index=True)
    component = Column(String(50), index=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Context
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_metrics_type_timestamp', 'metric_type', 'timestamp'),
    )

class ErrorLog(Base):
    """Error logging table."""
    
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    error_type = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    component = Column(String(100), index=True)
    
    # Request context
    request_id = Column(String(36), index=True)
    document_id = Column(String(64), index=True)
    client_ip = Column(String(45))
    
    # Stack trace
    stack_trace = Column(Text)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional context
    metadata = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index('idx_errors_type_timestamp', 'error_type', 'timestamp'),
        Index('idx_errors_component_timestamp', 'component', 'timestamp'),
    )
