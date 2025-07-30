"""
Custom exception classes for the application.
"""

class BaseAppException(Exception):
    """Base exception for application-specific errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class DocumentProcessingError(BaseAppException):
    """Exception raised when document processing fails."""
    pass

class EmbeddingGenerationError(BaseAppException):
    """Exception raised when embedding generation fails."""
    pass

class LLMProcessingError(BaseAppException):
    """Exception raised when LLM processing fails."""
    pass

class QueryProcessingError(BaseAppException):
    """Exception raised when query processing fails."""
    pass

class ValidationError(BaseAppException):
    """Exception raised when input validation fails."""
    pass

class CacheError(BaseAppException):
    """Exception raised when cache operations fail."""
    pass

class DatabaseError(BaseAppException):
    """Exception raised when database operations fail."""
    pass

class AuthenticationError(BaseAppException):
    """Exception raised when authentication fails."""
    pass

class RateLimitError(BaseAppException):
    """Exception raised when rate limit is exceeded."""
    pass
