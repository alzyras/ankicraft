"""Language detection utilities for the flashcard generator."""

import logging
from typing import Optional
import langdetect


def detect_language(text: str) -> str:
    """Detect the language of the given text.
    
    Args:
        text: Text to detect language for
        
    Returns:
        Detected language code (e.g., 'en', 'lt', 'de', etc.)
    """
    if not text:
        return 'en'  # Default to English

    # Extract a sample of the text (first 2000 characters to avoid performance issues)
    sample_text = text[:2000]
    
    # Using langdetect to detect the language
    try:
        # Use only a few sentences from the text for language detection to improve performance
        sentences = sample_text.split('.')
        if len(sentences) > 5:  # Use first 5 sentences for detection
            sample_text = '.'.join(sentences[:5]) + '.'

        # Detect language using langdetect
        detected_lang = langdetect.detect(sample_text)
        
        # Return the detected language code
        return detected_lang if detected_lang else 'en'
    
    except Exception as e:
        logging.warning(f"Language detection failed: {e}. Defaulting to 'en'.")
        # Fallback to the previous method if langdetect fails
        return _fallback_detect_language(sample_text)


def _fallback_detect_language(text: str) -> str:
    """Fallback language detection method using heuristics.
    
    Args:
        text: Text to detect language for
        
    Returns:
        Detected language code (e.g., 'en', 'lt', 'de', etc.)
    """
    if not text:
        return 'en'  # Default to English

    sample_text = text[:2000].lower()

    # Define language-specific character patterns and common words
    language_indicators = {
        'lt': {  # Lithuanian
            'characters': 'ąčęėįšųūžĄČĘĖĮŠŲŪŽ',
            'words': ['ir', 'yra', 'su', 'bei', 'tai', 'kad', 'nėra', 'arba', 'tik', 'bei'],
        },
        'en': {  # English
            'characters': '',
            'words': ['the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'that', 'this'],
        },
        'de': {  # German
            'characters': 'äöüßÄÖÜ',
            'words': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'],
        },
        'fr': {  # French
            'characters': 'àâäéèêëïîôöùûüÿçÀÂÄÉÈÊËÏÎÔÖÙÛÜŸÇ',
            'words': ['le', 'la', 'les', 'et', 'à', 'des', 'du', 'un', 'une', 'dans'],
        },
        'es': {  # Spanish
            'characters': 'áéíóúüñÁÉÍÓÚÜÑ',
            'words': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se'],
        },
        'ru': {  # Russian
            'characters': 'абвгдеёжзийклmnопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ',
            'words': ['и', 'в', 'не', 'на', 'я', 'быть', 'то', 'он', 'с', 'а'],
        }
    }

    # Count occurrences of language-specific characters
    char_scores = {}
    for lang, indicators in language_indicators.items():
        char_score = 0
        if indicators['characters']:
            for char in indicators['characters']:
                char_score += sample_text.count(char)
        char_scores[lang] = char_score

    # Count occurrences of language-specific words
    word_scores = {}
    for lang, indicators in language_indicators.items():
        word_score = 0
        for word in indicators['words']:
            # Count whole word matches (with word boundaries)
            import re
            pattern = r'\b' + re.escape(word) + r'\b'
            word_score += len(re.findall(pattern, sample_text))
        word_scores[lang] = word_score

    # Calculate combined scores
    combined_scores = {}
    for lang in language_indicators.keys():
        combined_scores[lang] = char_scores.get(lang, 0) * 10 + word_scores.get(lang, 0)

    # Return the language with the highest score
    if combined_scores:
        detected_lang = max(combined_scores, key=combined_scores.get)
        highest_score = combined_scores[detected_lang]

        # Only return detected language if it has a reasonable score
        if highest_score > 0:
            return detected_lang
        else:
            # Default to English if no strong indicators found
            return 'en'
    else:
        return 'en'


def get_language_name(language_code: str) -> str:
    """Get the full name of a language from its code.
    
    Args:
        language_code: Language code (e.g., 'en', 'lt')
        
    Returns:
        Full language name (e.g., 'English', 'Lithuanian')
    """
    language_names = {
        'en': 'English',
        'lt': 'Lithuanian',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'ru': 'Russian',
    }

    return language_names.get(language_code, language_code.capitalize())