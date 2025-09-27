"""Command-line interface for the flashcard generator."""

import argparse
import logging
import sys
from typing import List

from .processor import process_file, process_text


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Anki flashcards (simple Q&A format) from PDFs, websites, or text with three coverage levels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate flashcards from a PDF with medium coverage (default)
  python -m uv_app.flashcard_generator --input document.pdf
  
  # Generate flashcards with minimal coverage (fewer cards)
  python -m uv_app.flashcard_generator --input document.pdf --coverage minimal
  
  # Generate flashcards with maximum coverage (more cards)
  python -m uv_app.flashcard_generator --input document.pdf --coverage maximum
  
  # Generate flashcards from a website
  python -m uv_app.flashcard_generator --input https://example.com/article
  
  # Generate flashcards with custom instructions
  python -m uv_app.flashcard_generator --input document.pdf --prompt "Extract only dates"
  
  # Generate flashcards with a custom deck name
  python -m uv_app.flashcard_generator --input document.pdf --deck-name "History Notes"
        
Coverage Levels:
  minimal   - Only the most essential, distinctive facts from the entire book (~1 card per 20 pages)
  medium    - Balanced coverage of important concepts from the entire book (~1 card per 5 pages) 
  maximum   - Comprehensive coverage of ALL important facts from the entire book (~2-3 cards per page)
        
Note: Generates simple Q&A cards. All coverage options cover the entire book.
        """
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to PDF file or URL of webpage to process"
    )
    
    parser.add_argument(
        "--prompt", "-p",
        help="Custom instruction for extraction (e.g., 'extract only dates')"
    )
    
    parser.add_argument(
        "--deck-name", "-n",
        help="Custom name for the Anki deck"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        default="medium",
        choices=["minimal", "medium", "maximum"],
        help="Coverage level: minimal, medium, or maximum (default: medium)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    try:
        logging.info(f"Processing: {args.input}")
        
        # Process the input with specified coverage level
        output_file = process_file(
            file_path=args.input,
            user_prompt=args.prompt,
            deck_name=args.deck_name,
            coverage_level=args.coverage
        )
        
        logging.info(f"Anki deck created: {output_file}")
        print(f"Successfully created Anki deck: {output_file}")
        
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()