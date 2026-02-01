"""
Rate limiting middleware for Telegram bot.
Protects against spam and abuse.
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    # Messages per minute
    messages_per_minute: int = 20
    # Callbacks per minute
    callbacks_per_minute: int = 30
    # Voice messages per minute
    voice_per_minute: int = 5
    # Cooldown period in seconds after exceeding limit
    cooldown_seconds: int = 60


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        # user_id -> list of timestamps
        self._message_times: Dict[int, list] = defaultdict(list)
        self._callback_times: Dict[int, list] = defaultdict(list)
        self._voice_times: Dict[int, list] = defaultdict(list)
        # user_id -> cooldown_until timestamp
        self._cooldowns: Dict[int, float] = {}
    
    def _cleanup_old_entries(self, entries: list, window_seconds: int = 60) -> list:
        """Remove entries older than window."""
        cutoff = time.time() - window_seconds
        return [t for t in entries if t > cutoff]
    
    def is_rate_limited(self, user_id: int, action_type: str = "message") -> bool:
        """
        Check if user is rate limited.
        
        Args:
            user_id: Telegram user ID
            action_type: 'message', 'callback', or 'voice'
            
        Returns:
            True if rate limited
        """
        current_time = time.time()
        
        # Check cooldown
        if user_id in self._cooldowns:
            if current_time < self._cooldowns[user_id]:
                return True
            else:
                del self._cooldowns[user_id]
        
        # Get appropriate limit and storage
        if action_type == "voice":
            times = self._voice_times[user_id]
            limit = self.config.voice_per_minute
        elif action_type == "callback":
            times = self._callback_times[user_id]
            limit = self.config.callbacks_per_minute
        else:
            times = self._message_times[user_id]
            limit = self.config.messages_per_minute
        
        # Cleanup old entries
        times = self._cleanup_old_entries(times)
        
        # Check limit
        if len(times) >= limit:
            # Set cooldown
            self._cooldowns[user_id] = current_time + self.config.cooldown_seconds
            logger.warning(f"Rate limit exceeded: user_id={user_id}, action={action_type}")
            return True
        
        # Record this action
        times.append(current_time)
        
        # Update storage
        if action_type == "voice":
            self._voice_times[user_id] = times
        elif action_type == "callback":
            self._callback_times[user_id] = times
        else:
            self._message_times[user_id] = times
        
        return False
    
    def get_remaining_cooldown(self, user_id: int) -> int:
        """Get remaining cooldown seconds for user."""
        if user_id not in self._cooldowns:
            return 0
        remaining = self._cooldowns[user_id] - time.time()
        return max(0, int(remaining))


class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, rate_limiter: RateLimiter = None):
        self.rate_limiter = rate_limiter or RateLimiter()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Get user ID and action type
        user_id = None
        action_type = "message"
        
        if isinstance(event, Message):
            user_id = event.from_user.id
            if event.voice:
                action_type = "voice"
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            action_type = "callback"
        
        if user_id is None:
            return await handler(event, data)
        
        # Check rate limit
        if self.rate_limiter.is_rate_limited(user_id, action_type):
            # Send rate limit message
            from src.lexicon.lexicon_ru import LEXICON_RU
            
            if isinstance(event, Message):
                await event.answer(LEXICON_RU["error_too_fast"])
            elif isinstance(event, CallbackQuery):
                await event.answer(LEXICON_RU["error_too_fast"], show_alert=True)
            
            return None
        
        return await handler(event, data)


# Global rate limiter instance
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
