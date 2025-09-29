"""Simple card quality improvements."""

import logging
import re
from typing import List, Tuple


def improve_qa_cards(qa_cards: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Improve Q&A cards with simple quality checks.
    
    Args:
        qa_cards: List of (question, answer) tuples
        
    Returns:
        List of improved (question, answer) tuples
    """
    improved_cards = []
    
    for question, answer in qa_cards:
        # Apply simple quality improvements
        improved_question, improved_answer = _improve_single_qa_card(question, answer)
        improved_cards.append((improved_question, improved_answer))
    
    return improved_cards


def improve_cloze_cards(cloze_cards: List[str]) -> List[str]:
    """Improve cloze cards with simple quality checks.
    
    Args:
        cloze_cards: List of cloze deletion cards
        
    Returns:
        List of improved cloze cards
    """
    improved_cards = []
    
    for card in cloze_cards:
        # Apply simple quality improvements
        improved_card = _improve_single_cloze_card(card)
        improved_cards.append(improved_card)
    
    return improved_cards


def _improve_single_qa_card(question: str, answer: str) -> Tuple[str, str]:
    """Apply simple improvements to a single Q&A card."""
    # Basic cleanup
    question = question.strip()
    answer = answer.strip()
    
    # Ensure question ends with a question mark
    if not question.endswith("?"):
        question = question.rstrip(".") + "?"
    
    return question, answer


def _improve_single_cloze_card(card: str) -> str:
    """Apply simple improvements to a single cloze card."""
    # Basic cleanup
    return card.strip()