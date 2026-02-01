"""
Configuration module for finance bot.
Loads settings from environment variables.
"""
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from .base import getenv


@dataclass
class TelegramBotConfig:
    """Telegram bot configuration."""
    token: str


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/finance_bot.db"


@dataclass
class OpenRouterConfig:
    """OpenRouter LLM configuration."""
    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"


@dataclass
class WhisperConfig:
    """Whisper STT configuration."""
    model: str = "turbo"
    temp_dir: str = "data/temp_audio"


@dataclass
class Config:
    """Main application configuration."""
    tg_bot: TelegramBotConfig
    db: DatabaseConfig
    openrouter: OpenRouterConfig
    whisper: WhisperConfig


def load_config() -> Config:
    """Load configuration from environment variables."""
    # Parse a `.env` file and load the variables into environment variables
    load_dotenv()

    return Config(
        tg_bot=TelegramBotConfig(
            token=getenv("BOT_TOKEN")
        ),
        db=DatabaseConfig(
            path=getenv("DB_PATH", default="data/finance_bot.db")
        ),
        openrouter=OpenRouterConfig(
            api_key=getenv("OPENROUTER_API_KEY"),
            model=getenv("OPENROUTER_MODEL", default="arcee-ai/trinity-large-preview:free")
        ),
        whisper=WhisperConfig(
            model=getenv("WHISPER_MODEL", default="turbo"),
            temp_dir=getenv("WHISPER_TEMP_DIR", default="data/temp_audio")
        )
    )
