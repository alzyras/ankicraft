"""Flashcard generation utilities."""

import logging
import re
from typing import List, Tuple


def create_qa_flashcards(key_points: List[str]) -> List[Tuple[str, str]]:
    """Create simple Q&A flashcards from key points.
    
    Args:
        key_points: List of key points extracted from text
        
    Returns:
        List of (question, answer) tuples
    """
    flashcards = []
    
    for point in key_points:
        # Create simple Q&A cards
        qa_pairs = _create_simple_qa_cards(point)
        flashcards.extend(qa_pairs)
    
    return flashcards


def create_cloze_flashcards(key_points: List[str]) -> List[str]:
    """Create cloze deletion flashcards from key points.
    
    Args:
        key_points: List of key points extracted from text
        
    Returns:
        List of cloze deletion cards
    """
    flashcards = []
    
    for point in key_points:
        # Create simple cloze deletions
        cloze_cards = _create_simple_cloze_cards(point)
        flashcards.extend(cloze_cards)
    
    return flashcards


def _create_simple_qa_cards(statement: str) -> List[Tuple[str, str]]:
    """Create simple Q&A cards.
    
    Args:
        statement: Input statement
        
    Returns:
        List of (question, answer) tuples
    """
    qa_pairs = []
    
    # Remove the period at the end
    statement = statement.rstrip('.')
    
    # Pattern 1: Subject verb object in year
    # e.g., "Christopher Columbus's arrival in the Caribbean in 1492 marked the beginning"
    year_match = re.search(r'(.+?)\bin\s+(\d{4})\b(.+)', statement)
    if year_match:
        before_year, year, after_year = year_match.groups()
        # Create a question about what happened in that year
        qa_pairs.append((f"What happened in {year}?", statement))
        return qa_pairs
    
    # Pattern 2: X were Y (descriptive statements)
    # e.g., "The first Europeans to arrive in North America were Norse explorers"
    pattern2 = re.match(r'^(.+?)\s+(were|was|are)\s+(.+)', statement)
    if pattern2:
        subject, verb, description = pattern2.groups()
        qa_pairs.append((f"What {verb} {subject}?", description.strip()))
        return qa_pairs
    
    # Pattern 3: Subject, description, verb, object, year
    # e.g., "The Pilgrims, a group of Separatists, founded Plymouth Colony in 1620"
    pattern3 = re.match(r'^([^,]+),\s*([^,]+),\s*([a-zA-Z]+)\s+([^,]+)\s+in\s+(\d+)', statement)
    if pattern3:
        subject, description, verb, object, year = pattern3.groups()
        # Create specific questions
        qa_pairs.append((f"Who {verb} {object}?", subject.strip()))
        qa_pairs.append((f"What group {verb} {object}?", description.strip()))
        qa_pairs.append((f"When did {subject} {verb} {object}?", year.strip()))
        return qa_pairs
    
    # Pattern 4: Subject verb object (no year)
    # e.g., "The French established colonies in North America"
    pattern4 = re.match(r'^(The\s+[A-Za-z]+)\s+([a-zA-Z]+)\s+(.+)', statement)
    if pattern4:
        subject, verb, object = pattern4.groups()
        qa_pairs.append((f"Who {verb} {object}?", subject.strip()))
        return qa_pairs
    
    # If we can't create good specific questions, create a general temporal question for statements with years
    # Look for 4-digit years in the statement
    year_pattern = r'\b(\d{4})\b'
    years = re.findall(year_pattern, statement)
    for year in years:
        # Only consider reasonable historical years
        if 1000 <= int(year) <= 2025:
            qa_pairs.append((f"What happened in {year}?", statement))
            return qa_pairs
    
    # If we still can't create good questions, create a simple question about the statement
    if len(statement) > 10:
        qa_pairs.append((f"What is this fact?", statement))
    
    return qa_pairs


def _create_simple_cloze_cards(statement: str) -> List[str]:
    """Create simple cloze cards.
    
    Args:
        statement: Input statement
        
    Returns:
        List of cloze deletion cards
    """
    cloze_cards = []
    
    # Create multiple cloze cards, each with one deletion
    words = statement.split()
    
    # Identify key terms to delete (nouns, dates, important concepts)
    key_positions = []
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^\w]', '', word.lower())
        # Identify important words to hide
        if (len(clean_word) > 3 and 
            clean_word not in ["the", "and", "for", "with", "from", "this", "that", "were", "have", "been", "had"] and
            not (i > 0 and words[i-1].lower() == "a" and len(clean_word) <= 4)):
            key_positions.append(i)
    
    # Create one cloze card for each key term
    for pos in key_positions[:4]:  # Limit to 4 cloze deletions
        words_copy = words.copy()
        clean_word = re.sub(r'[^\w]', '', words_copy[pos])
        words_copy[pos] = "{{c1::" + clean_word + "}}"
        cloze_card = " ".join(words_copy) + "."
        cloze_cards.append(cloze_card)
    
    return cloze_cards