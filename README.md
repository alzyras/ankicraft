# Anki Decker - Flashcard Generator

Automatically generate flashcards from articles, research papers, or PDFs and export them to Anki.

## Features

- Extract text from PDF files or web articles
- Summarize key points using smart algorithms or AI models
- Generate Q&A flashcards (simple format)
- Export directly to Anki (.apkg) format
- Customize extraction with user prompts (e.g., "extract only dates")
- Support for both OpenAI and Transformers AI models
- Command-line interface for easy use

## Installation

To create and install virtual environment:

```bash
uv sync
```

During development, you can lint and format code using:

```bash
uv run poe x
```

To export requirements.txt:
```bash
uv export --no-hashes --no-dev --format requirements-txt > requirements.txt
```

## Configuration

The application can be configured using environment variables in a `.env` file:

```env
# AI Provider: "openai", "transformers", or "none" (for simple heuristics)
AI_PROVIDER=transformers

# OpenAI settings (only needed if AI_PROVIDER=openai)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Transformers settings (only needed if AI_PROVIDER=transformers)
TRANSFORMERS_MODEL=facebook/bart-large-cnn
```

## Usage

### Command Line Interface

Generate flashcards from a PDF:
```bash
uv run python -m uv_app.flashcard_generator --input document.pdf
```

Generate flashcards from a web article:
```bash
uv run python -m uv_app.flashcard_generator --input https://example.com/article
```

Generate flashcards with custom instructions:
```bash
uv run python -m uv_app.flashcard_generator --input document.pdf --prompt "Extract only dates"
```

Generate flashcards with a custom deck name:
```bash
uv run python -m uv_app.flashcard_generator --input document.pdf --deck-name "History Notes"
```

### Python API

You can also use the flashcard generator programmatically:

```python
from uv_app.flashcard_generator.processor import process_file, process_text

# Process a PDF file
output_file = process_file("document.pdf")

# Process a web article
output_file = process_file("https://example.com/article")

# Process with custom instructions
output_file = process_file("document.pdf", user_prompt="Extract only dates")

# Process plain text
output_file = process_text("Your text content here", deck_name="My Deck")
```

## How It Works

1. **Text Extraction**: Extracts text from PDF files using PyPDF2/pdfplumber or web articles using BeautifulSoup
2. **Document Structure Analysis**: Identifies chapters, sections, and metadata 
3. **Content Analysis**: Identifies key points using either:
   - Simple heuristics (default)
   - Transformers models (when AI_PROVIDER=transformers)
   - OpenAI models (when AI_PROVIDER=openai)
4. **Flashcard Generation**: Creates Q&A flashcards following Anki best practices
5. **Card Quality Assurance**: Applies best practices to ensure high-quality Anki cards:
   - Ensures questions ask exactly one thing
   - Makes questions specific and unambiguous
   - Converts yes/no questions to more informative formats
6. **Anki Export**: Exports flashcards to Anki-compatible .apkg format using genanki

*Note: Currently generates only Q&A cards. Cloze deletion cards may be added in a future version.*

## Coverage Levels

The system supports multiple coverage levels to suit different study needs. ALL COVERAGE LEVELS COVER THE ENTIRE BOOK - they differ only in density:

### Minimal Coverage (~1 card per 20 pages)
- Focuses only on the most essential, distinctive facts from the ENTIRE book
- Perfect for quick review or key highlight extraction
- Command: `--coverage minimal`

### Medium Coverage (~1 card per 5 pages) - DEFAULT
- Balanced coverage of important concepts from the ENTIRE book
- Good for regular study and comprehensive review
- Command: `--coverage medium` (default if no coverage specified)

### Maximum Coverage (~2-3 cards per page)
- Comprehensive coverage of ALL important facts from the ENTIRE book
- Detailed study with extensive coverage
- Command: `--coverage maximum`

## For Large Documents (Like Your 670-Page Book)

### Coverage Calculations:
- **Minimal**: ~34 cards (only the most essential facts from the ENTIRE 670-page book)
- **Medium**: ~134 cards (balanced comprehensive coverage of the ENTIRE 670-page book)  
- **Maximum**: ~1,500+ cards (comprehensive coverage of ALL important facts from the ENTIRE 670-page book)
- **Custom**: Any exact number you specify

### Processing Characteristics:
- **Minimal**: Fewer API calls, fastest processing
- **Medium**: Moderate API calls, balanced processing
- **Maximum**: More API calls, most comprehensive processing
- **Custom**: Scaled appropriately to reach your target

## Examples

### Basic Usage (Medium Coverage - Default)
```bash
# Generate flashcards from a PDF with balanced coverage
python -m uv_app.flashcard_generator --input document.pdf
```

### Minimal Coverage (Fewer Cards)
```bash
# Generate only the most essential facts
python -m uv_app.flashcard_generator --input document.pdf --coverage minimal
```

### Maximum Coverage (Every Statement)
```bash
# Generate comprehensive coverage of every meaningful statement
python -m uv_app.flashcard_generator --input document.pdf --coverage maximum
```

### Custom Number (Exact Amount)
```bash
# Generate exactly 150 cards
python -m uv_app.flashcard_generator --input document.pdf --coverage 150
```

### Custom Instructions
```bash
# Extract only dates and historical events
python -m uv_app.flashcard_generator --input document.pdf --prompt "Extract only dates and historical events"
```

### Custom Deck Name
```bash
# Generate flashcards with a custom deck name
python -m uv_app.flashcard_generator --input document.pdf --deck-name "History Notes"
```



## AI Model Options

### Transformers (Local Processing)
When `AI_PROVIDER=transformers`, the application uses local transformer models for content analysis. This option:
- Works offline
- No API costs
- Slower processing
- Requires more computational resources

### OpenAI API
When `AI_PROVIDER=openai`, the application uses OpenAI's API for content analysis. This option:
- Requires an API key
- Faster processing
- Higher accuracy
- Incurs API costs

### Simple Heuristics (Default)
When `AI_PROVIDER=none` or when AI libraries are not available, the application uses rule-based heuristics:
- No dependencies on external services
- Fastest processing
- Lower accuracy
- Completely free

## Card Quality Principles

The flashcard generator automatically applies best practices for creating high-quality Anki cards based on established principles:

1. **Atomic Questions**: Ensures each card asks exactly one thing
2. **Specific Questions**: Makes questions precise to permit exactly one answer
3. **Context-Free**: Creates questions that can be understood without external context
4. **Avoiding Yes/No**: Converts yes/no questions to more informative formats
5. **Improved Cloze Deletions**: Ensures cloze cards have appropriate deletions

These principles help create flashcards that are easier to review and more effective for long-term retention.

## Customization

You can customize the extraction process by providing a prompt:
- `"Extract only dates"` - Focuses on extracting sentences containing dates
- `"Extract scientific facts"` - Prioritizes scientific information
- `"Extract historical events"` - Focuses on historical information

By default, the system extracts important facts and nuances from the document.