"""
Text processing utilities for cleaning and chunking text.
"""

import re
import string
from typing import List, Tuple
import unicodedata

def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters but keep newlines and tabs
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    
    # Normalize line breaks
    text = re.sub(r'\r\n|\r', '\n', text)
    
    # Remove excessive newlines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text

def normalize_text(text: str) -> str:
    """
    Normalize text for comparison and processing.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation except periods and commas
    translator = str.maketrans('', '', string.punctuation.replace('.', '').replace(',', ''))
    text = text.translate(translator)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def split_text_into_chunks(
    text: str, 
    chunk_size: int = 512, 
    overlap: int = 50
) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    
    # First try to split by sentences
    sentences = extract_sentences(text)
    
    if not sentences:
        # Fallback to character-based splitting
        return _split_by_characters(text, chunk_size, overlap)
    
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed chunk size
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap from previous chunk
            if overlap > 0:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    # Add the last chunk if it has content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Handle very long sentences that exceed chunk_size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > chunk_size:
            # Split long chunks by characters
            sub_chunks = _split_by_characters(chunk, chunk_size, overlap)
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def extract_sentences(text: str) -> List[str]:
    """
    Extract sentences from text.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    if not text:
        return []
    
    # Simple sentence splitting pattern
    # This handles common abbreviations and decimal numbers
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+'
    
    sentences = re.split(sentence_pattern, text)
    
    # Clean and filter sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 10:  # Minimum sentence length
            cleaned_sentences.append(sentence)
    
    return cleaned_sentences

def _split_by_characters(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text by character count with overlap.
    
    Args:
        text: Text to split
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk
            chunks.append(text[start:])
            break
        
        # Try to break at word boundary
        chunk = text[start:end]
        last_space = chunk.rfind(' ')
        
        if last_space > chunk_size * 0.8:  # Only break at word if it's not too early
            chunk = text[start:start + last_space]
            start = start + last_space + 1
        else:
            start = end
        
        chunks.append(chunk.strip())
        
        # Adjust start for overlap
        if start < len(text):
            start = max(start - overlap, start - chunk_size // 4)
    
    return [chunk for chunk in chunks if chunk.strip()]

def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """
    Extract key phrases from text using simple heuristics.
    
    Args:
        text: Input text
        max_phrases: Maximum number of phrases to extract
        
    Returns:
        List of key phrases
    """
    if not text:
        return []
    
    # Clean text
    cleaned_text = normalize_text(text)
    words = cleaned_text.split()
    
    if len(words) < 3:
        return [text]
    
    phrases = []
    
    # Extract 2-3 word phrases
    for i in range(len(words) - 1):
        if i < len(words) - 2:
            three_word = ' '.join(words[i:i+3])
            if len(three_word) > 6:  # Minimum phrase length
                phrases.append(three_word)
        
        two_word = ' '.join(words[i:i+2])
        if len(two_word) > 4:
            phrases.append(two_word)
    
    # Remove duplicates and sort by length (longer phrases first)
    unique_phrases = list(set(phrases))
    unique_phrases.sort(key=len, reverse=True)
    
    return unique_phrases[:max_phrases]

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using word overlap.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    
    if not words1 or not words2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0
