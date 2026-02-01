"""
Input validation utilities.
Protects against malicious input and ensures data integrity.
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class InputValidator:
    """Validator for user inputs."""
    
    # Maximum text length
    MAX_TEXT_LENGTH = 500
    
    # Maximum category name length
    MAX_CATEGORY_NAME = 50
    
    # Maximum voice duration in seconds
    MAX_VOICE_DURATION = 300  # 5 minutes
    
    # Maximum file size in bytes (25 MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024
    
    # Minimum amount
    MIN_AMOUNT = 0.01
    
    # Maximum amount
    MAX_AMOUNT = 10_000_000
    
    # Suspicious patterns for logging
    SUSPICIOUS_PATTERNS = [
        r'(?i)drop\s+table',
        r'(?i)delete\s+from',
        r'(?i)insert\s+into',
        r'(?i)union\s+select',
        r'<script',
        r'javascript:',
        r'(?i)ignore\s+previous',
        r'(?i)system\s*prompt',
    ]
    
    @classmethod
    def validate_text(cls, text: str, user_id: int = None) -> Tuple[bool, str, Optional[str]]:
        """
        Validate text input.
        
        Returns:
            Tuple of (is_valid, sanitized_text, error_message)
        """
        if not text:
            return False, "", "Пустой текст"
        
        # Check length
        if len(text) > cls.MAX_TEXT_LENGTH:
            logger.info(f"Text too long: {len(text)} chars, user_id={user_id}")
            return False, "", f"Текст слишком длинный (макс. {cls.MAX_TEXT_LENGTH} символов)"
        
        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"Suspicious pattern detected: user_id={user_id}, pattern={pattern}")
                # Don't reject, just log and sanitize
        
        # Sanitize: remove control characters except newlines
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return True, sanitized, None
    
    @classmethod
    def validate_category_name(cls, name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate category name.
        
        Returns:
            Tuple of (is_valid, sanitized_name, error_message)
        """
        if not name:
            return False, "", "Название не может быть пустым"
        
        # Trim and limit length
        sanitized = name.strip()[:cls.MAX_CATEGORY_NAME]
        
        if len(sanitized) < 1:
            return False, "", "Название не может быть пустым"
        
        # Remove special characters except basic punctuation
        sanitized = re.sub(r'[^\w\s\-.,!?()]', '', sanitized)
        
        return True, sanitized, None
    
    @classmethod
    def validate_amount(cls, amount: float) -> Tuple[bool, Optional[str]]:
        """
        Validate transaction amount.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount < cls.MIN_AMOUNT:
            return False, "Сумма слишком маленькая"
        
        if amount > cls.MAX_AMOUNT:
            return False, "Сумма слишком большая"
        
        return True, None
    
    @classmethod
    def validate_voice_message(cls, duration: int, file_size: int, user_id: int = None) -> Tuple[bool, Optional[str]]:
        """
        Validate voice message parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if duration > cls.MAX_VOICE_DURATION:
            logger.info(f"Voice too long: {duration}s, user_id={user_id}")
            return False, f"Голосовое слишком длинное (макс. {cls.MAX_VOICE_DURATION // 60} минут)"
        
        if file_size > cls.MAX_FILE_SIZE:
            logger.info(f"Voice file too large: {file_size} bytes, user_id={user_id}")
            return False, "Файл слишком большой"
        
        return True, None


class SecurityLogger:
    """Logger for security-related events."""
    
    _logger = logging.getLogger("security")
    
    @classmethod
    def log_suspicious_activity(cls, user_id: int, activity_type: str, details: str = None):
        """Log suspicious activity."""
        cls._logger.warning(f"SUSPICIOUS: user_id={user_id}, type={activity_type}, details={details}")
    
    @classmethod
    def log_rate_limit_exceeded(cls, user_id: int, action_type: str):
        """Log rate limit exceeded."""
        cls._logger.info(f"RATE_LIMIT: user_id={user_id}, action={action_type}")
    
    @classmethod
    def log_validation_failure(cls, user_id: int, field: str, reason: str):
        """Log validation failure."""
        cls._logger.info(f"VALIDATION_FAIL: user_id={user_id}, field={field}, reason={reason}")
    
    @classmethod
    def log_transaction(cls, user_id: int, amount: float, transaction_type: str, category: str):
        """Log successful transaction."""
        cls._logger.info(f"TRANSACTION: user_id={user_id}, amount={amount}, type={transaction_type}, category={category}")
