"""
File handling utilities for document processing.
"""

import hashlib
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
import httpx

async def download_file(url: str, max_size_mb: int = 50) -> bytes:
    """
    Download file from URL with size limit.
    
    Args:
        url: File URL
        max_size_mb: Maximum file size in MB
        
    Returns:
        File content as bytes
        
    Raises:
        ValueError: If file is too large or download fails
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream('GET', url) as response:
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > max_size_mb:
                    raise ValueError(f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB)")
            
            # Download in chunks
            content = b''
            async for chunk in response.aiter_bytes(chunk_size=8192):
                content += chunk
                
                # Check accumulated size
                if len(content) > max_size_mb * 1024 * 1024:
                    raise ValueError(f"File too large (max: {max_size_mb}MB)")
    
    return content

def get_file_hash(content: bytes) -> str:
    """
    Calculate MD5 hash of file content.
    
    Args:
        content: File content
        
    Returns:
        MD5 hash as hex string
    """
    return hashlib.md5(content).hexdigest()

def detect_file_type(content: bytes, filename: Optional[str] = None) -> Tuple[str, str]:
    """
    Detect file type from content and filename.
    
    Args:
        content: File content
        filename: Optional filename
        
    Returns:
        Tuple of (mime_type, extension)
    """
    # Try to detect from content
    import magic
    try:
        mime_type = magic.from_buffer(content, mime=True)
    except:
        mime_type = 'application/octet-stream'
    
    # Try to get from filename
    if filename:
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            mime_type = guessed_type
    
    # Determine extension
    extension = mimetypes.guess_extension(mime_type) or ''
    
    return mime_type, extension

async def save_temp_file(content: bytes, suffix: str = '') -> str:
    """
    Save content to temporary file.
    
    Args:
        content: File content
        suffix: File suffix/extension
        
    Returns:
        Path to temporary file
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content)
        return temp_file.name

async def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up temporary file.
    
    Args:
        file_path: Path to file to delete
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception:
        pass  # Ignore cleanup errors

def ensure_directory(directory: str) -> None:
    """
    Ensure directory exists.
    
    Args:
        directory: Directory path
    """
    Path(directory).mkdir(parents=True, exist_ok=True)

async def read_file_async(file_path: str) -> str:
    """
    Read file content asynchronously.
    
    Args:
        file_path: Path to file
        
    Returns:
        File content as string
    """
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
        return await file.read()

async def write_file_async(file_path: str, content: str) -> None:
    """
    Write content to file asynchronously.
    
    Args:
        file_path: Path to file
        content: Content to write
    """
    # Ensure directory exists
    ensure_directory(os.path.dirname(file_path))
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
        await file.write(content)
