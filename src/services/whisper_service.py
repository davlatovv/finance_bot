"""
Whisper service for speech-to-text conversion.
Handles voice message processing from Telegram.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Union

import whisper

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for converting speech to text using OpenAI Whisper."""
    
    # Maximum audio file size (25 MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024
    
    # Maximum audio duration (5 minutes)
    MAX_DURATION_SECONDS = 300
    
    def __init__(self, model_name: str = "turbo", temp_dir: Optional[str] = None):
        """
        Initialize Whisper service.
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large, turbo)
            temp_dir: Directory for temporary audio files
        """
        self.model_name = model_name
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
        self._model: Optional[whisper.Whisper] = None
        
        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def model(self) -> whisper.Whisper:
        """Lazy load Whisper model."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self._model = whisper.load_model(self.model_name)
            logger.info("Whisper model loaded successfully")
        return self._model
    
    async def transcribe_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Transcribe audio file to text.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Transcribed text or None if failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return None
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            logger.warning(f"Audio file too large: {file_size} bytes")
            return None
        
        try:
            logger.info(f"Transcribing audio file: {file_path}")
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                str(file_path),
                language="ru",  # Russian language
                task="transcribe",
                fp16=False  # Disable FP16 for CPU compatibility
            )
            
            text = result.get("text", "").strip()
            
            if text:
                logger.info(f"Transcription successful: {len(text)} chars")
                return self._normalize_text(text)
            else:
                logger.warning("Transcription returned empty text")
                return None
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize transcribed text.
        
        - Remove extra whitespace
        - Fix common transcription errors
        - Clean up punctuation
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove leading/trailing punctuation artifacts
        text = text.strip('.,!?;:')
        
        return text
    
    def get_temp_file_path(self, user_id: int, file_id: str) -> Path:
        """
        Get path for temporary audio file.
        
        Args:
            user_id: Telegram user ID
            file_id: Telegram file ID
            
        Returns:
            Path for temporary file
        """
        # Use hash of file_id for filename to avoid collisions
        safe_name = f"{user_id}_{file_id[-16:]}.ogg"
        return self.temp_dir / safe_name
    
    def cleanup_temp_file(self, file_path: Path) -> None:
        """Remove temporary audio file."""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")


# Global service instance
_whisper_service: Optional[WhisperService] = None


def get_whisper_service(model_name: str = "turbo", temp_dir: Optional[str] = None) -> WhisperService:
    """Get or create Whisper service instance."""
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService(model_name=model_name, temp_dir=temp_dir)
    return _whisper_service
