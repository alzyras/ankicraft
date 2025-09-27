"""AI-powered text processing utilities."""

import logging
from typing import List, Optional, Tuple

from ..settings import FlashcardSettings

settings = FlashcardSettings()


def extract_key_points_ai(text: str, user_prompt: Optional[str] = None) -> List[str]:
    """Extract key points from text using AI models.
    
    Args:
        text: Input text to extract key points from
        user_prompt: Optional user instruction (e.g., "extract only dates")
        
    Returns:
        List of key points
    """
    if settings.AI_PROVIDER == "openai":
        return _extract_with_openai(text, user_prompt)
    elif settings.AI_PROVIDER == "transformers":
        return _extract_with_transformers(text, user_prompt)
    else:
        # Fallback to simple extraction
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)


def generate_qa_cards_ai(text: str, user_prompt: Optional[str] = None, target_cards: Optional[int] = None) -> List[Tuple[str, str]]:
    """Generate Q&A cards from text using AI models.
    
    Args:
        text: Input text to generate Q&A cards from
        user_prompt: Optional user instruction
        target_cards: Target number of cards to generate
        
    Returns:
        List of (question, answer) tuples
    """
    if settings.AI_PROVIDER == "openai":
        return _generate_qa_with_openai(text, user_prompt, target_cards)
    elif settings.AI_PROVIDER == "transformers":
        # For transformers, fall back to key point extraction + QA generation
        key_points = _extract_with_transformers(text, user_prompt)
        return _generate_qa_from_key_points(key_points)
    else:
        # Fallback to simple extraction + QA generation
        from ..flashcard_generator.summarizer import extract_key_points_simple
        key_points = extract_key_points_simple(text, user_prompt)
        return _generate_qa_from_key_points(key_points)


def _extract_with_openai(text: str, user_prompt: Optional[str] = None) -> List[str]:
    """Extract key points using OpenAI API.
    
    Args:
        text: Input text to extract key points from
        user_prompt: Optional user instruction
        
    Returns:
        List of key points
    """
    try:
        import openai
    except ImportError:
        logging.warning("OpenAI library not installed. Falling back to simple extraction.")
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)
    
    if not settings.OPENAI_API_KEY:
        logging.warning("OpenAI API key not set. Falling back to simple extraction.")
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)
    
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Construct the prompt for better key point extraction
        if user_prompt:
            system_message = f"You are an expert at extracting key information and facts from text. {user_prompt}"
        else:
            system_message = "You are an expert at extracting key information and facts from text. Extract the most important facts and key points."
        
        user_message = f"""Extract key facts and important points from the following text. Format each point as a separate sentence:\n\n{text}"""
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Parse the response
        content = response.choices[0].message.content
        # Split into points (assuming they're separated by newlines)
        points = [point.strip() for point in content.split("\n") if point.strip()]
        # Remove numbering/bullets
        points = [point.lstrip("0123456789. -–—*") for point in points]
        
        return points[:15]  # Limit to 15 key points
    except Exception as e:
        logging.error(f"Error extracting key points with OpenAI: {e}")
        # Fallback to simple extraction
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)


def _generate_qa_with_openai(text: str, user_prompt: Optional[str] = None, target_cards: Optional[int] = None) -> List[Tuple[str, str]]:
    """Generate Q&A cards using OpenAI API.
    
    Args:
        text: Input text to generate Q&A cards from
        user_prompt: Optional user instruction
        target_cards: Target number of cards to generate
        
    Returns:
        List of (question, answer) tuples
    """
    try:
        import openai
    except ImportError:
        logging.warning("OpenAI library not installed. Falling back to simple extraction.")
        return _fallback_qa_generation(text, user_prompt)
    
    if not settings.OPENAI_API_KEY:
        logging.warning("OpenAI API key not set. Falling back to simple extraction.")
        return _fallback_qa_generation(text, user_prompt)
    
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Calculate document density to determine question count
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = len([s for s in text.split('.') if s.strip()])
        
        # Estimate information density (facts/concepts per 1000 characters)
        density_score = (word_count / char_count) * (sentence_count / max(word_count, 1)) * 1000
        
        # Calculate pages estimate
        pages_estimate = char_count / 2500  # Roughly 2500 chars per page
        
        # Use provided target or calculate default
        if target_cards is not None:
            # If explicit target is provided, use it directly
            target_questions = target_cards
        else:
            # Calculate default based on document analysis
            if pages_estimate <= 30:  # Short document (≤30 pages)
                target_questions = max(10, min(25, int(word_count / 200)))  # 10-25 questions
            elif pages_estimate <= 100:  # Medium document (≤100 pages)
                target_questions = max(20, min(50, int(word_count / 250)))  # 20-50 questions
            elif pages_estimate <= 300:  # Long document (≤300 pages)
                target_questions = max(30, min(80, int(word_count / 280)))  # 30-80 questions
            else:  # Very long document (>300 pages)
                # For very long documents, scale based on content but cap for practicality
                target_questions = max(40, min(3000, int(word_count / 200)))  # 40-3000 questions
        
        logging.info(f"Document analysis - Pages: {pages_estimate:.0f}, Characters: {char_count}, Words: {word_count}, Density: {density_score:.2f}, Target questions: {target_questions}")
        
        # Handle large texts by chunking
        max_tokens = 70000  # Conservative token limit
        if char_count > max_tokens:
            logging.info("Text is too long for QA generation, chunking it")
            chunks = _split_text_into_chunks(text, max_tokens)
            
            # Calculate questions per chunk based on target
            chunks_to_process = min(15, len(chunks))  # Up to 15 chunks
            questions_per_chunk = max(10, target_questions // chunks_to_process)
            
            all_qa_pairs = []
            
            # Extract key facts and concepts from each chunk
            for i, chunk in enumerate(chunks[:chunks_to_process]):
                logging.info(f"Generating QA for chunk {i+1}/{chunks_to_process} (target: {questions_per_chunk} questions)")
                
                # Construct the prompt for QA generation
                if user_prompt:
                    system_message = f"You are an expert at creating educational flashcards. {user_prompt}"
                else:
                    system_message = "You are an expert at creating educational flashcards. Create meaningful questions that cover important concepts in the text."
                
                user_message = f"""Create {questions_per_chunk-2}-{questions_per_chunk+2} Q&A flashcards from the following text.
Cover important facts, dates, people, events, and concepts in the text.
Each question should:
1. Ask exactly one specific thing
2. Not give away the answer in the question
3. Be clear and unambiguous
4. Test important concepts from the text
5. Focus on key facts that students should remember

Format each flashcard as:
Q: [question]
A: [answer]

Text:
{chunk}"""
                
                try:
                    response = client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0.4,  # Lower temperature for more consistent extraction
                        max_tokens=min(2500, 200 + (questions_per_chunk * 80))  # Scale tokens with question count
                    )
                    
                    # Parse the response
                    content = response.choices[0].message.content
                    qa_pairs = _parse_qa_response(content)
                    all_qa_pairs.extend(qa_pairs)
                except Exception as chunk_error:
                    logging.error(f"Error generating QA for chunk {i+1}: {chunk_error}")
                    continue
            
            # Deduplicate QA pairs
            seen_questions = set()
            unique_qa_pairs = []
            for q, a in all_qa_pairs:
                if q not in seen_questions and len(q) > 10 and len(a) > 5:
                    seen_questions.add(q)
                    unique_qa_pairs.append((q, a))
            
            return unique_qa_pairs[:target_questions]  # Return target number of questions
        else:
            # Construct the prompt for QA generation
            if user_prompt:
                system_message = f"You are an expert at creating educational flashcards. {user_prompt}"
            else:
                system_message = "You are an expert at creating educational flashcards. Create meaningful questions that cover important concepts in the text."
            
            user_message = f"""Create {max(10, target_questions-5)}-{target_questions+5} Q&A flashcards from the following text.
Cover important facts, dates, people, events, and concepts in the text.
Each question should:
1. Ask exactly one specific thing
2. Not give away the answer in the question
3. Be clear and unambiguous
4. Test important concepts from the text
5. Focus on key facts that students should remember

Format each flashcard as:
Q: [question]
A: [answer]

Text:
{text}"""
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.4,
                max_tokens=min(3500, 600 + (target_questions * 75))  # Scale tokens with question count
            )
            
            # Parse the response
            content = response.choices[0].message.content
            qa_pairs = _parse_qa_response(content)
            
            # Filter out low-quality pairs
            filtered_pairs = [(q, a) for q, a in qa_pairs if len(q) > 10 and len(a) > 5]
            return filtered_pairs[:target_questions]  # Return target number of questions
    except Exception as e:
        logging.error(f"Error generating QA cards with OpenAI: {e}")
        # Fallback to simple extraction
        return _fallback_qa_generation(text, user_prompt)


def _split_text_into_chunks(text: str, max_chunk_size: int) -> List[str]:
    """Split text into chunks of maximum size.
    
    Args:
        text: Text to split
        max_chunk_size: Maximum size of each chunk
        
    Returns:
        List of text chunks
    """
    # Split by paragraphs first to avoid breaking sentences
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk.strip():
            # Save current chunk
            chunks.append(current_chunk.strip())
            # Start new chunk with this paragraph
            current_chunk = paragraph + "\n\n"
        else:
            # Add paragraph to current chunk
            current_chunk += paragraph + "\n\n"
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # If we still have chunks that are too large, split them further
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_chunk_size:
            final_chunks.append(chunk)
        else:
            # Split by sentences
            sentences = chunk.split('. ')
            sub_chunk = ""
            for sentence in sentences:
                if len(sub_chunk) + len(sentence) > max_chunk_size:
                    if sub_chunk.strip():
                        final_chunks.append(sub_chunk.strip())
                    sub_chunk = sentence + ". "
                else:
                    sub_chunk += sentence + ". "
            if sub_chunk.strip():
                final_chunks.append(sub_chunk.strip())
    
    return final_chunks


def _parse_qa_response(content: str) -> List[Tuple[str, str]]:
    """Parse QA pairs from AI response.
    
    Args:
        content: AI response content
        
    Returns:
        List of (question, answer) tuples
    """
    qa_pairs = []
    lines = content.split('\n')
    
    current_question = None
    current_answer = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('Q:') or line.startswith('Question:'):
            if current_question and current_answer:
                qa_pairs.append((current_question, current_answer))
            current_question = line.split(':', 1)[1].strip() if ':' in line else line[2:].strip()
            current_answer = None
        elif line.startswith('A:') or line.startswith('Answer:'):
            current_answer = line.split(':', 1)[1].strip() if ':' in line else line[2:].strip()
        elif current_question and not current_answer and line:
            # If we have a question but no answer yet, this might be the answer
            if not line.startswith(('Q:', 'Question:', 'A:', 'Answer:')):
                current_answer = line
    
    # Add the last pair if it exists
    if current_question and current_answer:
        qa_pairs.append((current_question, current_answer))
    
    return qa_pairs


def _extract_with_transformers(text: str, user_prompt: Optional[str] = None) -> List[str]:
    """Extract key points using transformers.
    
    Args:
        text: Input text to extract key points from
        user_prompt: Optional user instruction
        
    Returns:
        List of key points
    """
    try:
        from transformers import pipeline
    except ImportError:
        logging.warning("Transformers library not installed. Falling back to simple extraction.")
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)
    
    try:
        # Use a question-answering model to extract key points
        # For now, we'll use a summarization approach
        summarizer = pipeline("summarization", model=settings.TRANSFORMERS_MODEL)
        
        # For very long texts, we need to chunk them
        max_length = 1024
        if len(text) > max_length:
            # Simple chunking approach
            chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            summaries = []
            for chunk in chunks:
                try:
                    summary = summarizer(chunk, max_length=150, min_length=30, do_sample=False)
                    summaries.append(summary[0]['summary_text'])
                except:
                    continue
            combined_summary = " ".join(summaries)
        else:
            summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
            combined_summary = summary[0]['summary_text']
        
        # Split summary into key points
        import re
        sentences = re.split(r'[.!?]+', combined_summary)
        points = [s.strip() for s in sentences if s.strip()]
        
        return points[:15]  # Limit to 15 key points
    except Exception as e:
        logging.error(f"Error extracting key points with transformers: {e}")
        # Fallback to simple extraction
        from ..flashcard_generator.summarizer import extract_key_points_simple
        return extract_key_points_simple(text, user_prompt)


def _generate_qa_from_key_points(key_points: List[str]) -> List[Tuple[str, str]]:
    """Generate Q&A cards from key points.
    
    Args:
        key_points: List of key points
        
    Returns:
        List of (question, answer) tuples
    """
    qa_pairs = []
    for point in key_points:
        # Simple approach: Turn statements into questions
        # In a production environment, you might use a more sophisticated NLP model
        question = _convert_statement_to_question(point)
        qa_pairs.append((question, point))
    
    return qa_pairs


def _convert_statement_to_question(statement: str) -> str:
    """Convert a statement to a question format.
    
    Args:
        statement: Input statement
        
    Returns:
        Question format of the statement
    """
    # Simple heuristics for converting statements to questions
    statement = statement.strip()
    
    # If it starts with a verb, prefix with "What"
    if statement.lower().startswith(("is", "are", "was", "were", "has", "have", "had", 
                                   "do", "does", "did", "can", "could", "will", "would", 
                                   "should", "may", "might")):
        return statement.rstrip('.') + "?"
    
    # If it contains "is", "are", etc., try to form a question
    if any(word in statement.lower() for word in ["is", "are", "was", "were"]):
        return statement.rstrip('.') + "?"
    
    # Default: prefix with "What is"
    return "What is " + statement.rstrip('.') + "?"


def _fallback_qa_generation(text: str, user_prompt: Optional[str] = None) -> List[Tuple[str, str]]:
    """Fallback QA generation using simple extraction.
    
    Args:
        text: Input text
        user_prompt: Optional user instruction
        
    Returns:
        List of (question, answer) tuples
    """
    from ..flashcard_generator.summarizer import extract_key_points_simple
    key_points = extract_key_points_simple(text, user_prompt)
    
    if key_points:
        from .flashcard_generator import create_qa_flashcards
        return create_qa_flashcards(key_points)
    
    return []