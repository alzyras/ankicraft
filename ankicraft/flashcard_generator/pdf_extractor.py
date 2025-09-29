"""PDF text extraction utilities."""

import logging
import re
from typing import Dict, List, Optional, Tuple


def extract_text_from_pdf_pypdf2(file_path: str) -> Optional[str]:
    """Extract text from a PDF file using PyPDF2.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import PyPDF2
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        logging.error(f"Error extracting text with PyPDF2: {e}")
        return None


def extract_text_from_pdf_pdfplumber(file_path: str) -> Optional[str]:
    """Extract text from a PDF file using pdfplumber.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        logging.error(f"Error extracting text with pdfplumber: {e}")
        return None


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text from a PDF file using the best available method.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    # Try pdfplumber first (better for complex layouts)
    text = extract_text_from_pdf_pdfplumber(file_path)
    if text:
        return text
    
    # Fallback to PyPDF2
    return extract_text_from_pdf_pypdf2(file_path)


def identify_document_structure(text: str) -> Dict[str, any]:
    """Identify the document structure including chapters, sections, and metadata.
    
    Args:
        text: Text to analyze for document structure
        
    Returns:
        Dictionary with document structure information
    """
    structure = {
        'chapters': {},
        'sections': [],
        'metadata': {},
        'toc': []
    }
    
    # Extract metadata from beginning of document
    lines = text.split('\n')[:100]  # First 100 lines
    
    # Look for title (usually the first substantial capitalized line)
    for line in lines:
        line = line.strip()
        if line and len(line) > 10 and line.isupper() and not line.startswith(('TABLE', 'CONTENTS', 'INDEX')):
            structure['metadata']['title'] = line.title()  # Convert to title case
            break
    
    # Look for author
    author_patterns = [
        r'(?:Author|AUTHOR|By|BY)[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:Written by|WRITTEN BY)[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:Edited by|EDITED BY)[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    ]
    
    for pattern in author_patterns:
        author_match = re.search(pattern, text[:2000], re.IGNORECASE)
        if author_match:
            structure['metadata']['author'] = author_match.group(1).strip()
            break
    
    # Extract table of contents if present
    toc_patterns = [
        r'(?:Table of Contents|TABLE OF CONTENTS|Contents|CONTENTS)(.*?)(?:\n\s*\n|\Z)',
        r'(?:Table Of Contents|table of contents)(.*?)(?:\n\s*\n|\Z)',
    ]
    
    for pattern in toc_patterns:
        toc_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if toc_match:
            toc_text = toc_match.group(1)
            # Extract chapter/section entries from TOC
            toc_entries = re.findall(r'(\d+\.\d*|\w+)\.?\s+([A-Z][A-Za-z\s]+)\s*\.*\s*(\d+)', toc_text)
            structure['toc'] = toc_entries
            break
    
    # Extract chapters based on common patterns
    chapter_patterns = [
        r'(?:Chapter|CHAPTER|Ch\.|CH\.)\s+(\d+\.?\s*[A-Za-z]*)[:\-]?\s*([^.]+)',  # Chapter 1: Title
        r'(?:Chapter|CHAPTER|Ch\.|CH\.)\s+([IVX]+\.?\s*[A-Za-z]*)[:\-]?\s*([^.]+)',  # Chapter I: Title
        r'(\d+\.\s+[A-Z][A-Za-z\s]+)',  # 1. Introduction
        r'([IVX]+\.\s+[A-Z][A-Za-z\s]+)',  # I. Introduction
    ]
    
    # Find all chapter headings
    found_chapters = {}
    for pattern in chapter_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            if len(match.groups()) >= 2:
                chapter_num, chapter_title = match.groups()
                chapter_name = f"Chapter {chapter_num}: {chapter_title}"
                # Extract text until next chapter or end
                start_pos = match.end()
                # Find next chapter heading
                next_match = None
                for next_pattern in chapter_patterns:
                    next_match = re.search(next_pattern, text[start_pos:])
                    if next_match:
                        break
                if next_match:
                    end_pos = start_pos + next_match.start()
                    chapter_text = text[start_pos:end_pos]
                else:
                    chapter_text = text[start_pos:]
                if len(chapter_text.strip()) > 500:  # Only keep substantial chapters
                    found_chapters[chapter_name] = chapter_text.strip()
            else:
                chapter_name = match.group(1).strip()
                # Extract text until next chapter or end
                start_pos = match.end()
                # Find next chapter heading
                next_match = None
                for next_pattern in chapter_patterns:
                    next_match = re.search(next_pattern, text[start_pos:])
                    if next_match:
                        break
                if next_match:
                    end_pos = start_pos + next_match.start()
                    chapter_text = text[start_pos:end_pos]
                else:
                    chapter_text = text[start_pos:]
                if len(chapter_text.strip()) > 500:  # Only keep substantial chapters
                    found_chapters[chapter_name] = chapter_text.strip()
    
    structure['chapters'] = found_chapters
    
    # Extract sections if no clear chapters found
    if not found_chapters:
        section_patterns = [
            r'\n\s*\n([A-Z][A-Za-z\s]{10,}[:.])\s*\n',  # CAPITOL TITLE:
            r'\n\s*\n(\d+\.\s+[A-Z][A-Za-z\s]+[:.])\s*\n',  # 1. Introduction:
        ]
        
        found_sections = []
        for pattern in section_patterns:
            matches = re.findall(pattern, text)
            found_sections.extend(matches)
        
        structure['sections'] = found_sections[:20]  # Limit to 20 sections
    
    return structure