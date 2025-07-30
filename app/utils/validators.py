"""
Input validation utilities.
"""

import re
from typing import List, Optional
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def validate_bearer_token(token: str, expected_token: str) -> bool:
    """
    Validate bearer token.
    
    Args:
        token: Token to validate
        expected_token: Expected token value
        
    Returns:
        True if valid, False otherwise
    """
    if not token or not expected_token:
        return False
    
    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    return token == expected_token

def validate_questions(questions: List[str]) -> List[str]:
    """
    Validate list of questions.
    
    Args:
        questions: List of questions to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not questions:
        errors.append("At least one question is required")
        return errors
    
    if len(questions) > 20:
        errors.append("Maximum 20 questions allowed")
    
    for i, question in enumerate(questions, 1):
        if not question or not question.strip():
            errors.append(f"Question {i} cannot be empty")
            continue
        
        question = question.strip()
        if len(question) < 3:
            errors.append(f"Question {i} too short (minimum 3 characters)")
        
        if len(question) > 500:
            errors.append(f"Question {i} too long (maximum 500 characters)")
    
    return errors

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove excessive dots and spaces
    filename = re.sub(r'\.{2,}', '.', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename

def validate_chunk_size(chunk_size: int) -> bool:
    """
    Validate chunk size parameter.
    
    Args:
        chunk_size: Chunk size to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 100 <= chunk_size <= 2000

def validate_similarity_threshold(threshold: float) -> bool:
    """
    Validate similarity threshold.
    
    Args:
        threshold: Threshold to validate
        
    Returns:
        True if valid, False otherwise
    """
    return 0.0 <= threshold <= 1.0
