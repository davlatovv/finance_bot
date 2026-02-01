"""
LLM service for processing user messages via OpenRouter.
Handles transaction parsing and categorization.
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from src.llm.prompts import SYSTEM_PROMPT, get_transaction_prompt
from src.llm.tools import get_tools

logger = logging.getLogger(__name__)


@dataclass
class TransactionData:
    """Parsed transaction data from LLM."""
    amount: float
    type: str  # 'income' or 'expense'
    category_name: str
    description: Optional[str] = None
    new_category: bool = False  # True if category needs to be created


@dataclass
class LLMResponse:
    """Response from LLM processing."""
    success: bool
    transaction: Optional[TransactionData] = None
    error: Optional[str] = None


class LLMService:
    """Service for processing messages via OpenRouter LLM."""
    
    # Request timeout
    TIMEOUT = 60.0
    
    # Max input text length
    MAX_TEXT_LENGTH = 500
    
    def __init__(self, api_key: str, model: str, base_url: str = "https://openrouter.ai/api/v1"):
        """
        Initialize LLM service.
        
        Args:
            api_key: OpenRouter API key
            model: Model identifier (e.g., 'arcee-ai/trinity-large-preview:free')
            base_url: OpenRouter API base URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.TIMEOUT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/finance-bot",
                    "X-Title": "Finance Bot"
                }
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize user input to prevent prompt injection.
        
        - Limit length
        - Remove potential injection patterns
        - Normalize whitespace
        """
        # Limit length
        text = text[:self.MAX_TEXT_LENGTH]
        
        # Remove potential system prompt injections
        injection_patterns = [
            r'system\s*:', r'assistant\s*:', r'user\s*:',
            r'\[INST\]', r'\[/INST\]', r'<<SYS>>', r'<</SYS>>',
            r'ignore\s+(previous|above)\s+instructions',
            r'forget\s+(previous|above|all)',
        ]
        
        for pattern in injection_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def process_transaction(
        self, 
        user_text: str, 
        transaction_type: str,
        categories: list[dict]
    ) -> LLMResponse:
        """
        Process user message to extract transaction data.
        
        Args:
            user_text: User's message about the transaction
            transaction_type: 'income' or 'expense'
            categories: List of user's existing categories
            
        Returns:
            LLMResponse with parsed transaction data
        """
        # Sanitize input
        sanitized_text = self._sanitize_input(user_text)
        
        if not sanitized_text:
            return LLMResponse(success=False, error="Пустое сообщение")
        
        # Build prompt
        user_prompt = get_transaction_prompt(sanitized_text, transaction_type, categories)
        
        try:
            # Call OpenRouter API
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "tools": get_tools(),
                    "tool_choice": "auto",
                    "temperature": 0.1,  # Low temperature for consistent parsing
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return LLMResponse(success=False, error="Ошибка API")
            
            result = response.json()
            return self._parse_response(result, transaction_type, sanitized_text)
            
        except httpx.TimeoutException:
            logger.error("OpenRouter API timeout")
            return LLMResponse(success=False, error="Таймаут запроса")
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            return LLMResponse(success=False, error="Ошибка обработки")
    
    def _parse_response(
        self, 
        response: dict, 
        default_type: str,
        raw_text: str
    ) -> LLMResponse:
        """Parse LLM response and extract transaction data."""
        try:
            message = response.get("choices", [{}])[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if not tool_calls:
                # No tool calls - try to extract from content
                content = message.get("content", "")
                logger.warning(f"No tool calls in response, content: {content}")
                
                # Fallback: try to parse amount from user text
                return self._fallback_parse(raw_text, default_type)
            
            # Process tool calls
            new_category = None
            transaction = None
            
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                func_name = func.get("name")
                
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    continue
                
                if func_name == "create_category":
                    new_category = args.get("name")
                    
                elif func_name == "create_transaction":
                    transaction = TransactionData(
                        amount=float(args.get("amount", 0)),
                        type=args.get("type", default_type),
                        category_name=args.get("category_name", "Другое"),
                        description=args.get("description"),
                        new_category=False
                    )
            
            if transaction:
                # Check if category was created in this request
                if new_category and transaction.category_name == new_category:
                    transaction.new_category = True
                
                return LLMResponse(success=True, transaction=transaction)
            
            # Fallback if no transaction parsed
            return self._fallback_parse(raw_text, default_type)
            
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return LLMResponse(success=False, error="Ошибка разбора ответа")
    
    def _fallback_parse(self, text: str, transaction_type: str) -> LLMResponse:
        """
        Fallback parsing when LLM doesn't return proper tool calls.
        Extracts amount using regex patterns.
        """
        # Try to find amount in text
        amount = 0.0
        
        # Pattern for numbers with optional currency
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:тыс|к)\b',  # 5к, 5 тыс
            r'(\d+(?:[.,]\d+)?)\s*(?:сўм|so''m|сум|uzs)\b',  # 50000 сўм
            r'(\d+(?:[.,]\d+)?)',  # Just numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(',', '.')
                amount = float(num_str)
                
                # Check for thousands multiplier
                if 'тыс' in text.lower() or re.search(r'\d+\s*к\b', text, re.IGNORECASE):
                    amount *= 1000
                break
        
        # Create fallback transaction
        transaction = TransactionData(
            amount=amount,
            type=transaction_type,
            category_name="Другое",
            description=text[:100],
            new_category=True
        )
        
        return LLMResponse(success=True, transaction=transaction)


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service(api_key: str, model: str, base_url: str = "https://openrouter.ai/api/v1") -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(api_key=api_key, model=model, base_url=base_url)
    return _llm_service


async def close_llm_service() -> None:
    """Close LLM service."""
    global _llm_service
    if _llm_service:
        await _llm_service.close()
        _llm_service = None
