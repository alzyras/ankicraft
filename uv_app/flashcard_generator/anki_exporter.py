"""Anki export utilities."""

import logging
import uuid
from typing import List, Tuple, Optional

import genanki


def create_anki_deck(
    qa_flashcards: List[Tuple[str, str]], 
    cloze_flashcards: List[str], 
    deck_name: str
) -> genanki.Deck:
    """Create an Anki deck from flashcards.
    
    Args:
        qa_flashcards: List of (question, answer) tuples
        cloze_flashcards: List of cloze deletion cards
        deck_name: Name for the Anki deck
        
    Returns:
        genanki.Deck object
    """
    # Generate a random deck ID
    deck_id = int(uuid.uuid4().hex[:8], 16)
    
    # Create the deck
    deck = genanki.Deck(deck_id, deck_name)
    
    # Create models for QA cards with professional styling
    qa_model = genanki.Model(
        int(uuid.uuid4().hex[:8], 16),
        'QA Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer"><div class="answer">{{Answer}}</div>',
            },
        ],
        css='''
        .card {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 32px;
            text-align: center;
            color: #2c3e50;
            background-color: #ffffff;
            padding: 30px;
            margin: 0;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            min-height: 400px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .answer {
            color: #27ae60;
            font-weight: 500;
        }
        .cloze {
            font-weight: bold;
            color: #e74c3c;
        }
        .card a {
            color: #3498db;
        }
        '''
    )
    
    # Create cloze model if needed
    cloze_model = genanki.Model(
        int(uuid.uuid4().hex[:8], 16),
        'Cloze Model',
        model_type=genanki.Model.CLOZE,
        fields=[
            {'name': 'Text'},
            {'name': 'Extra'},
        ],
        templates=[
            {
                'name': 'Cloze',
                'qfmt': '{{cloze:Text}}',
                'afmt': '{{cloze:Text}}<hr id="answer"><div class="answer">{{cloze:Text}}</div><div class="extra">{{Extra}}</div>',
            },
        ],
        css='''
        .card {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 32px;
            text-align: center;
            color: #2c3e50;
            background-color: #ffffff;
            padding: 30px;
            margin: 0;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            min-height: 400px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .answer {
            color: #27ae60;
            font-weight: 500;
        }
        .cloze {
            font-weight: bold;
            color: #e74c3c;
        }
        .extra {
            font-size: 24px;
            color: #7f8c8d;
            margin-top: 15px;
        }
        .card a {
            color: #3498db;
        }
        '''
    )
    
    # Add QA flashcards to deck
    for question, answer in qa_flashcards:
        note = genanki.Note(
            model=qa_model,
            fields=[question, answer],
        )
        deck.add_note(note)
    
    # Add cloze flashcards to deck if any exist
    for cloze_text in cloze_flashcards:
        note = genanki.Note(
            model=cloze_model,
            fields=[cloze_text, ''],
        )
        deck.add_note(note)
    
    return deck


def export_to_anki_package(deck: genanki.Deck, output_file: str) -> None:
    """Export an Anki deck to a .apkg file.
    
    Args:
        deck: genanki.Deck object
        output_file: Path to output .apkg file
    """
    genanki.Package(deck).write_to_file(output_file)