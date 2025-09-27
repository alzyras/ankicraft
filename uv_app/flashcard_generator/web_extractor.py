"""Web article extraction utilities."""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup


def extract_text_from_url(url: str) -> Optional[str]:
    """Extract text content from a web URL.
    
    Args:
        url: The URL to extract text from
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        logging.error(f"Error extracting text from URL {url}: {e}")
        return None