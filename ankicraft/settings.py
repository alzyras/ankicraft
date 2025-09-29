from dotenv import find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        validate_default=False,
    )

    EXAMPLE_ENV_VARIABLE: str


class WebSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        validate_default=False,
    )

    # Web server settings
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8080
    WEB_DEBUG: bool = False


class FlashcardSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        validate_default=False,
    )

    # This setting is no longer used - coverage level now determines the number of cards
    DEFAULT_FLASHCARD_COUNT: int = 20
    
    # Default deck name
    DEFAULT_DECK_NAME: str = "Generated Flashcards"
    
    # AI Model settings
    AI_PROVIDER: str = "transformers"  # "transformers", "openai", or "none"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Transformers settings
    TRANSFORMERS_MODEL: str = "facebook/bart-large-cnn"
