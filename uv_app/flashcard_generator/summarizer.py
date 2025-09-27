"""Text summarization and key point extraction utilities."""

import logging
from typing import List, Optional, Tuple

from .ai_processor import extract_key_points_ai, generate_qa_cards_ai


def extract_key_points_simple(text: str, user_prompt: Optional[str] = None) -> List[str]:
    """Extract key points from text using simple heuristics.
    
    Args:
        text: Input text to extract key points from
        user_prompt: Optional user instruction (e.g., "extract only dates")
        
    Returns:
        List of key points
    """
    # Split text into sentences
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    key_points = []
    
    # If user wants dates only
    if user_prompt and "date" in user_prompt.lower():
        # Simple date pattern matching
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YY or MM-DD-YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY-MM-DD
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}\b',  # Month DD, YYYY
        ]
        
        for sentence in sentences:
            for pattern in date_patterns:
                dates = re.findall(pattern, sentence)
                if dates:
                    key_points.append(sentence)
                    break
        return key_points[:10]  # Limit to 10 date-related sentences
    
    # Default behavior - extract important sentences based on simple heuristics
    # Look for sentences with numbers, capitalized words, or certain keywords
    important_indicators = [
        r'\d+',  # Contains numbers
        r'\b[A-Z]{2,}\b',  # Contains acronyms/abbreviations
        r'\b(?:important|significant|key|main|primary|crucial|essential|vital)\b',
        r'\b(?:according to|research|study|findings|results)\b',
    ]
    
    for sentence in sentences:
        # Skip very short sentences
        if len(sentence) < 20:
            continue
            
        # Check if sentence matches any important indicators
        for pattern in important_indicators:
            if re.search(pattern, sentence, re.IGNORECASE):
                key_points.append(sentence)
                break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_points = []
    for point in key_points:
        if point not in seen:
            seen.add(point)
            unique_points.append(point)
    
    # Limit to 15 key points
    return unique_points[:15]


def extract_key_points(text: str, user_prompt: Optional[str] = None) -> List[str]:
    """Extract key points from text using the configured AI method.
    
    Args:
        text: Input text to extract key points from
        user_prompt: Optional user instruction (e.g., "extract only dates")
        
    Returns:
        List of key points
    """
    # Use AI-powered extraction if enabled
    return extract_key_points_ai(text, user_prompt)


def generate_qa_cards(text: str, user_prompt: Optional[str] = None, target_cards: Optional[int] = None) -> List[Tuple[str, str]]:
    """Generate Q&A cards from text using the configured AI method.
    
    Args:
        text: Input text to generate Q&A cards from
        user_prompt: Optional user instruction
        target_cards: Target number of cards to generate
        
    Returns:
        List of (question, answer) tuples
    """
    # Use AI-powered QA generation if enabled
    return generate_qa_cards_ai(text, user_prompt, target_cards)


def summarize_text_simple(text: str, max_length: int = 200) -> str:
    """Generate a simple summary of the text.
    
    Args:
        text: Input text to summarize
        max_length: Maximum length of summary
        
    Returns:
        Summarized text
    """
    # For a simple approach, we'll take the first few sentences
    # In a real implementation, you might use a transformer model
    sentences = text.split('.')
    summary = ''
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) > max_length:
            break
        summary += sentence.strip() + '. '
        current_length += len(sentence) + 2
        
        if len(summary.split()) > 30:  # Roughly 30 words
            break
    
    return summary.strip()