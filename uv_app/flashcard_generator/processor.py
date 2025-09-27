"""Main flashcard generator processor."""

import logging
import os
from typing import List, Optional, Tuple
import re

from ..settings import FlashcardSettings
from .anki_exporter import create_anki_deck, export_to_anki_package
from .pdf_extractor import extract_text_from_pdf
from .summarizer import extract_key_points, generate_qa_cards
from .web_extractor import extract_text_from_url

# Load settings
settings = FlashcardSettings()


def process_file(
    file_path: str, 
    user_prompt: Optional[str] = None,
    deck_name: Optional[str] = None,
    coverage_level: str = "medium"
) -> str:
    """Process a file (PDF, text, or URL) and generate an Anki deck with simple QA cards.
    
    Args:
        file_path: Path to a file or URL
        user_prompt: Optional user instruction for customizing extraction
        deck_name: Optional name for the Anki deck
        coverage_level: Coverage level ("minimal", "medium", "maximum")
        
    Returns:
        Path to the generated .apkg file
    """
    # Extract text based on file type
    if file_path.startswith("http"):
        text = extract_text_from_url(file_path)
        if not deck_name:
            deck_name = f"Web Article - {file_path.split('/')[-1] or file_path.split('/')[-2]}"
    else:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine file type and extract text accordingly
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
            if not deck_name:
                deck_name = f"PDF - {os.path.basename(file_path).replace('.pdf', '')}"
        else:
            # Treat as plain text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            if not deck_name:
                deck_name = f"Text - {os.path.basename(file_path)}"
    
    if not text:
        raise ValueError("Failed to extract text from the provided source")
    
    # Determine target number of cards based on coverage level
    target_cards = _calculate_target_cards(text, coverage_level)
    
    # Generate Q&A flashcards with coverage level
    logging.info(f"Generating {target_cards} Q&A flashcards with {coverage_level} coverage...")
    qa_flashcards = _generate_qa_cards(text, user_prompt, target_cards, coverage_level)
    
    # Split into questions and answers
    qa_pairs = [(q, a) for q, a in qa_flashcards]
    
    cloze_flashcards = []  # Empty list for now
    
    logging.info(f"Generated {len(qa_pairs)} Q&A flashcards (target: {target_cards})")
    
    # Create Anki deck
    deck = create_anki_deck(qa_pairs, cloze_flashcards, deck_name)
    
    # Export to Anki package
    output_file = f"{deck_name.replace(' ', '_').lower()}.apkg"
    export_to_anki_package(deck, output_file)
    
    return output_file


def process_text(
    text: str, 
    user_prompt: Optional[str] = None,
    deck_name: str = None,
    coverage_level: str = "medium"
) -> str:
    """Process text and generate an Anki deck with simple QA cards.
    
    Args:
        text: Input text to process
        user_prompt: Optional user instruction for customizing extraction
        deck_name: Name for the Anki deck
        coverage_level: Coverage level ("minimal", "medium", "maximum")
        
    Returns:
        Path to the generated .apkg file
    """
    if not deck_name:
        deck_name = settings.DEFAULT_DECK_NAME
    
    # Determine target number of cards based on coverage level
    target_cards = _calculate_target_cards(text, coverage_level)
    
    # Generate Q&A flashcards with coverage level
    logging.info(f"Generating {target_cards} Q&A flashcards with {coverage_level} coverage...")
    qa_flashcards = _generate_qa_cards(text, user_prompt, target_cards, coverage_level)
    
    # Split into questions and answers
    qa_pairs = [(q, a) for q, a in qa_flashcards]
    
    cloze_flashcards = []  # Empty list for now
    
    logging.info(f"Generated {len(qa_pairs)} Q&A flashcards (target: {target_cards})")
    
    # Create Anki deck
    deck = create_anki_deck(qa_pairs, cloze_flashcards, deck_name)
    
    # Export to Anki package
    output_file = f"{deck_name.replace(' ', '_').lower()}.apkg"
    export_to_anki_package(deck, output_file)
    
    return output_file


def _calculate_target_cards(text: str, coverage_level: str) -> int:
    """Calculate target number of cards based on document size and coverage level.
    
    Args:
        text: Text to analyze
        coverage_level: "minimal", "medium", or "maximum"
        
    Returns:
        Target number of cards
    """
    char_count = len(text)
    pages_estimate = char_count / 2500  # Roughly 2500 chars per page
    
    # Calculate target based on coverage level
    # All coverage levels cover the ENTIRE book, but with different density
    if coverage_level == "minimal":
        # Minimal: Only the most essential facts from the ENTIRE book
        # ~1 card per 20 pages for the most important content across the whole book
        target = max(10, min(200, int(pages_estimate / 20)))
    elif coverage_level == "medium":
        # Medium: Balanced coverage of important concepts from the ENTIRE book
        # ~1 card per 5 pages across the whole book
        target = max(20, min(800, int(pages_estimate / 5)))
    elif coverage_level == "maximum":
        # Maximum: Comprehensive coverage of ALL important facts from the ENTIRE book
        # ~2-3 cards per page across the whole book
        target = max(50, min(5000, int(pages_estimate * 2)))
    else:
        # Default to medium
        logging.warning(f"Invalid coverage level '{coverage_level}', defaulting to 'medium'")
        target = max(20, min(800, int(pages_estimate / 5)))
    
    return target


def _generate_qa_cards(
    text: str, 
    user_prompt: Optional[str], 
    target_cards: int, 
    coverage_level: str
) -> List[Tuple[str, str]]:
    """Generate Q&A cards with specified coverage level.
    
    Args:
        text: Input text to process
        user_prompt: Optional user instruction
        target_cards: Target number of cards
        coverage_level: Coverage level ("minimal", "medium", "maximum")
        
    Returns:
        List of (question, answer) tuples
    """
    logging.info(f"Generating {target_cards} Q&A flashcards with {coverage_level} coverage")
    
    # Generate QA cards with the specified coverage level
    qa_flashcards = generate_qa_cards(text, user_prompt, target_cards)
    
    # Remove duplicates while preserving order
    seen_questions = set()
    unique_qa_flashcards = []
    for q, a in qa_flashcards:
        if q not in seen_questions and len(q) > 10 and len(a) > 5:
            seen_questions.add(q)
            unique_qa_flashcards.append((q, a))
    
    # If we have significantly fewer cards than target, do a final pass across the entire document
    if len(unique_qa_flashcards) < target_cards * 0.7:
        logging.info("Performing final pass to reach target...")
        remaining_cards = target_cards - len(unique_qa_flashcards)
        # Focus on what might have been missed
        final_cards = generate_qa_cards(text, 
                                      f"{user_prompt or ''} Extract important content that may have been missed", 
                                      remaining_cards)
        unique_qa_flashcards.extend(final_cards)
    
    # Remove duplicates again
    seen_questions = set()
    final_qa_flashcards = []
    for q, a in unique_qa_flashcards:
        if q not in seen_questions and len(q) > 10 and len(a) > 5:
            seen_questions.add(q)
            final_qa_flashcards.append((q, a))
    
    return final_qa_flashcards[:target_cards]


def _split_text_into_chapters(text: str) -> List[Tuple[str, str]]:
    """Split text into chapters/sections.
    
    Args:
        text: Text to split
        
    Returns:
        List of (chapter_title, chapter_text) tuples
    """
    # Simple chapter detection
    import re
    
    # Look for common chapter/section patterns
    chapter_patterns = [
        r'(?:Chapter|CHAPTER|Ch\.|CH\.)\s+(\d+\.?\s*[A-Za-z]*)[:\-]?\s*([^.]+)',  # Chapter 1: Title
        r'(?:Chapter|CHAPTER|Ch\.|CH\.)\s+([IVX]+\.?\s*[A-Za-z]*)[:\-]?\s*([^.]+)',  # Chapter I: Title
        r'(\d+\.?\s+[A-Z][A-Za-z\s]+)',  # 1. Introduction
        r'([IVX]+\.?\s+[A-Z][A-Za-z\s]+)',  # I. Introduction
        r'([A-Z][A-Za-z\s]{10,}[:.])\s*\n',  # Section Title:
    ]
    
    # Try each pattern
    for pattern in chapter_patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) >= 2:  # Use this pattern if we found at least 2 matches
            chapters = []
            start_pos = 0
            
            for match in matches:
                # Get the complete title
                title = match.group(0).strip()
                
                # Find the start of the chapter content (after the title line)
                chapter_start = match.end()
                
                # Find the start of the next chapter (or end of text)
                next_start = len(text)
                for next_match in matches:
                    if next_match.start() > match.start():
                        next_start = next_match.start()
                        break
                
                # Extract the content between this chapter and next
                chapter_text = text[chapter_start:next_start].strip()
                
                if len(chapter_text) > 300:  # Only include if substantial text
                    chapters.append((title, chapter_text))
            
            if len(chapters) >= 1:  # Found at least 1 chapter
                return chapters

    # If no clear chapters found, split by major sections
    # Look for section breaks with capitalization
    sections = re.split(r'\n\s*\n([A-Z][A-Z\s]{5,}[.:\n])', text)
    
    # Reconstruct sections with their titles
    if len(sections) >= 3:  # Pattern would create [text, title, text, title, ...]
        structured_sections = []
        i = 0
        while i < len(sections):
            if i + 1 < len(sections):
                section_title = sections[i].strip()  # This is actually the title
                section_content = sections[i+1].strip()  # This is the content
                if len(section_content) > 500:  # Only include substantial content
                    structured_sections.append((section_title, section_content))
                i += 2
            else:
                # Remaining content without a title
                remaining_content = sections[i].strip()
                if len(remaining_content) > 500:
                    structured_sections.append((f"Section {len(structured_sections)+1}", remaining_content))
                i += 1
        if structured_sections:
            return structured_sections
    
    # If still no clear sections, split by paragraph count
    paragraphs = text.split('\n\n')
    min_sections = min(10, len(paragraphs))  # Ensure we have multiple sections
    section_size = max(1, len(paragraphs) // min_sections)  # Create at least 10 sections if possible
    
    sections = []
    for i in range(0, len(paragraphs), section_size):
        section = '\n\n'.join(paragraphs[i:i+section_size])
        if len(section.strip()) > 300:  # Only include sections with content
            sections.append((f"Section {len(sections)+1}", section))
    
    if sections:
        return sections
    
    # Fallback: return the entire text as one section
    return [("Full Document", text)]