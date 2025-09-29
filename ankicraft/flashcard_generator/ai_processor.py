"""AI-powered text processing utilities."""

import logging
from typing import List, Optional, Tuple
import re

from ..settings import FlashcardSettings
from .language_detector import detect_language, get_language_name

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
        
        user_message = f"""Extract key facts and important points from the following text. Format each point as a separate sentence:

{text}"""
        
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
            
            # Detect the language of the document from the first chunk or a sample
            sample_text = text[:min(5000, len(text))]  # Use first 5000 characters for language detection
            detected_language = detect_language(sample_text)
            language_name = get_language_name(detected_language)
            logging.info(f"Detected document language: {language_name} ({detected_language})")
            
            # Calculate questions per chunk based on target
            chunks_to_process = len(chunks)  # Allow processing all chunks, not limited to 15
            questions_per_chunk = max(10, target_questions // chunks_to_process)
            
            # For maximum coverage, significantly increase the number of questions per chunk and aim to get more content covered
            if target_cards > 500:  # Maximum coverage level
                # In maximum coverage, request significantly more questions per chunk to ensure comprehensive coverage
                questions_per_chunk = max(questions_per_chunk, 30)  # Increase to at least 30 questions per chunk for max coverage
            
            all_qa_pairs = []
            
            # Extract key facts and concepts from each chunk
            for i, chunk in enumerate(chunks[:chunks_to_process]):
                logging.info(f"Generating QA for chunk {i+1}/{chunks_to_process} (target: {questions_per_chunk} questions)")
                
                # Construct the prompt for QA generation in the detected language
                if user_prompt:
                    system_message = f"You are an expert at creating educational flashcards in {language_name}. {user_prompt}"
                else:
                    system_message = f"You are an expert at creating educational flashcards in {language_name}. Create meaningful questions that cover important concepts in the text."
                
                user_message = f"""Create {questions_per_chunk-2}-{questions_per_chunk+2} Q&A flashcards from the following text in {language_name}.
Cover important facts, dates, people, events, and concepts in the text.
Each question should:
1. Ask exactly one specific thing
2. Not give away the answer in the question
3. Be clear and unambiguous
4. Test important concepts from the text
5. Focus on key facts that students should remember
6. Ensure comprehensive coverage - include ALL important content from the text
7. Include sufficient context in questions - for historical content spanning decades, include the time period, historical context, or relevant background information
8. Make questions self-contained so they can be understood without referring to the original text

Format each flashcard as:
Q: [question in {language_name} with sufficient context]
A: [answer in {language_name}]

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
                        max_tokens=min(4000, 300 + (questions_per_chunk * 100))  # Increase max tokens to allow more questions
                    )
                    
                    # Parse the response
                    content = response.choices[0].message.content
                    qa_pairs = _parse_qa_response(content)
                    all_qa_pairs.extend(qa_pairs)
                except Exception as chunk_error:
                    logging.error(f"Error generating QA for chunk {i+1}: {chunk_error}")
                    continue
            
            # For maximum coverage, use less strict deduplication to preserve more unique content
            seen_questions = set()
            unique_qa_pairs = []
            if target_questions > 500:  # Maximum coverage mode
                # In maximum mode, be less strict about deduplication to preserve more content
                for q, a in all_qa_pairs:
                    # Use a more lenient check for similarity to preserve more variety
                    is_duplicate = False
                    for seen_q in seen_questions:
                        # Simple similarity check - if questions share many common words, consider them similar
                        q_words = set(q.lower().split())
                        seen_words = set(seen_q.lower().split())
                        if len(q_words.intersection(seen_words)) > max(2, len(q_words) * 0.5):  # If 50% or more words match (more lenient)
                            is_duplicate = True
                            break
                    
                    if not is_duplicate and len(q) > 3 and len(a) > 2:  # Even more lenient filtering
                        seen_questions.add(q)
                        unique_qa_pairs.append((q, a))
            else:
                # For non-maximum modes, use the original stricter deduplication
                for q, a in all_qa_pairs:
                    if q not in seen_questions and len(q) > 10 and len(a) > 5:
                        seen_questions.add(q)
                        unique_qa_pairs.append((q, a))
            
            # If we still have significantly fewer cards than target in maximum mode, 
            # try to add more by using different prompts on the original text
            if target_questions > 500 and len(unique_qa_pairs) < target_questions * 0.8:
                logging.info(f"Maximum mode: Generated only {len(unique_qa_pairs)} cards out of target {target_questions}, supplementing with additional content processing...")
                
                # Use the original text to generate more questions with different focus
                try:
                    import openai
                    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                    
                    # Create a focused prompt for the remaining cards
                    remaining_target = target_questions - len(unique_qa_pairs)
                    focus_prompt = f"Generate {min(remaining_target, 50)} additional Q&A flashcards focusing on specific historical events, dates, people, and statistics from the text in {language_name}. Be as specific as possible."
                    
                    additional_user_message = f"""{focus_prompt}

                    Format each flashcard as:
                    Q: [specific question in {language_name} with full context]
                    A: [detailed answer in {language_name}]

                    Text:
                    {text[:max_tokens]}"""  # Use first part of text to avoid exceeding token limits
                    
                    additional_response = client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": additional_user_message}
                        ],
                        temperature=0.4,
                        max_tokens=min(3000, 300 + (min(remaining_target, 50) * 80))
                    )
                    
                    additional_content = additional_response.choices[0].message.content
                    additional_qa_pairs = _parse_qa_response(additional_content)
                    
                    # Add the additional pairs using the same lenient filtering
                    for q, a in additional_qa_pairs:
                        is_duplicate = False
                        for seen_q in seen_questions:
                            q_words = set(q.lower().split())
                            seen_words = set(seen_q.lower().split())
                            if len(q_words.intersection(seen_words)) > max(2, len(q_words) * 0.5):  # If 50% or more words match
                                is_duplicate = True
                                break
                        
                        if not is_duplicate and len(q) > 3 and len(a) > 2:
                            seen_questions.add(q)
                            unique_qa_pairs.append((q, a))
                            
                except Exception as e:
                    logging.error(f"Error generating additional cards: {e}")
            
            return unique_qa_pairs[:target_questions]  # Return target number of questions
        else:
            # Detect the language of the document
            detected_language = detect_language(text)
            language_name = get_language_name(detected_language)
            logging.info(f"Detected document language: {language_name} ({detected_language})")
            
            # For maximum coverage, ensure comprehensive processing with contextual questions
            if target_questions > 500:  # Maximum coverage level
                # In maximum coverage, request comprehensive coverage of the text
                user_message_base = f"""Create {max(10, target_questions-5)}-{target_questions+5} Q&A flashcards from the following text in {language_name}.
Cover ALL important facts, dates, people, events, and concepts in the text.
Each question should:
1. Ask exactly one specific thing
2. Not give away the answer in the question
3. Be clear and unambiguous
4. Test important concepts from the text
5. Focus on key facts that students should remember
6. Ensure comprehensive coverage - include ALL important content from the text
7. Include sufficient context in questions - for historical content spanning decades, include the time period, historical context, or relevant background information
8. Make questions self-contained so they can be understood without referring to the original text
"""
            else:
                user_message_base = f"""Create {max(10, target_questions-5)}-{target_questions+5} Q&A flashcards from the following text in {language_name}.
Cover important facts, dates, people, events, and concepts in the text.
Each question should:
1. Ask exactly one specific thing
2. Not give away the answer in the question
3. Be clear and unambiguous
4. Test important concepts from the text
5. Focus on key facts that students should remember
"""

            # Construct the prompt for QA generation in the detected language
            if user_prompt:
                system_message = f"You are an expert at creating educational flashcards in {language_name}. {user_prompt}"
            else:
                system_message = f"You are an expert at creating educational flashcards in {language_name}. Create meaningful questions that cover important concepts in the text."
            
            user_message = f"""{user_message_base}

Format each flashcard as:
Q: [question in {language_name}]
A: [answer in {language_name}]

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
            
            # For maximum coverage, use more lenient quality filtering
            if target_questions > 500:  # Maximum coverage mode
                # In maximum mode, be more lenient with filtering to preserve more content
                filtered_pairs = [(q, a) for q, a in qa_pairs if len(q) > 5 and len(a) > 3]
            else:
                # For non-maximum modes, use the original stricter filtering
                filtered_pairs = [(q, a) for q, a in qa_pairs if len(q) > 10 and len(a) > 5]
            
            return filtered_pairs[:target_questions]  # Return target number of questions
    except Exception as e:
        logging.error(f"Error generating QA cards with OpenAI: {e}")
        # Fallback to simple extraction
        return _fallback_qa_generation(text, user_prompt)


def _split_text_into_chunks(text: str, max_chunk_size: int) -> List[str]:
    """Split text into chunks of maximum size while preserving content meaning.
    
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
            # Split by sentences but ensure continuity
            sentences = chunk.split('. ')
            sub_chunk = ""
            sentence_count = 0
            target_sentences_per_subchunk = max(5, max_chunk_size // 500)  # Ensure we have reasonable number of sentences per chunk
            
            for sentence in sentences:
                sentence_with_punct = sentence.strip() + ". "
                
                if len(sub_chunk) + len(sentence_with_punct) > max_chunk_size and sub_chunk.strip():
                    # If we've added significant content, save the sub-chunk
                    if len(sub_chunk) > max_chunk_size // 4:  # At least 25% of max size
                        final_chunks.append(sub_chunk.strip())
                        sub_chunk = sentence_with_punct
                        sentence_count = 1
                    else:
                        # If sub-chunk is still small, just add to it
                        sub_chunk += sentence_with_punct
                        sentence_count += 1
                else:
                    sub_chunk += sentence_with_punct
                    sentence_count += 1
                    
                    # If we have reached a good number of sentences, consider starting a new chunk
                    if sentence_count >= target_sentences_per_subchunk and len(sub_chunk) > max_chunk_size // 3:
                        final_chunks.append(sub_chunk.strip())
                        sub_chunk = ""
                        sentence_count = 0
            
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
        # Handle various formats for questions (English, Lithuanian, and other formats)
        if (line.startswith('Q:') or 
            line.startswith('Question:') or 
            line.lower().startswith('k:') or  # Lithuanian 'K:' for 'Klausimas'
            line.lower().startswith('klausimas:')):  # Lithuanian 'Klausimas:'
            
            if current_question and current_answer:
                qa_pairs.append((current_question, current_answer))
            current_question = line.split(':', 1)[1].strip() if ':' in line else line[len('Klausimas:'):].strip() if 'klausimas:' in line.lower() else line[2:].strip()
            current_answer = None
        elif (line.startswith('A:') or 
              line.startswith('Answer:') or 
              line.lower().startswith('a:') or  # Lithuanian 'A:' for 'Atsakymas'
              line.lower().startswith('atsakymas:')):  # Lithuanian 'Atsakymas:'
            
            current_answer = line.split(':', 1)[1].strip() if ':' in line else line[len('Atsakymas:'):].strip() if 'atsakymas:' in line.lower() else line[2:].strip()
        elif current_question and not current_answer and line:
            # If we have a question but no answer yet, this might be the answer
            if not any(line.startswith(prefix) for prefix in ['Q:', 'Question:', 'A:', 'Answer:', 'K:', 'k:', 'A:', 'a:', 'Klausimas:', 'Atsakymas:']):
                current_answer = line
    
    # Add the last pair if it exists
    if current_question and current_answer:
        qa_pairs.append((current_question, current_answer))
    
    # In maximum coverage mode, try to extract QA pairs from alternative formats as well
    if len(qa_pairs) < 5:  # If we got very few pairs, try alternative parsing
        # Try to find Q: A: pairs on the same line
        import re
        same_line_pattern = r'(?:Q:|Question:|K:|Klausimas:)\s*(.*?)\s*(?:A:|Answer:|A:|Atsakymas:)\s*(.*?)(?=(?:\n|$|Q:|Question:|K:|Klausimas:))'
        matches = re.findall(same_line_pattern, content, re.IGNORECASE | re.DOTALL)
        for question, answer in matches:
            qa_pairs.append((question.strip(), answer.strip()))
    
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