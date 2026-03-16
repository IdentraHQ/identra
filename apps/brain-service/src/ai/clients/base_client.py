"""
Base AI Client Interface

Defines the common contract that all external AI providers must implement.
Ensures consistent behavior across Claude, OpenAI, and Gemini integrations.
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger("ai_clients")

class ModelProvider(str, Enum):
    """Supported AI providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    HUGGINGFACE = "huggingface"

class AIMessage(BaseModel):
    """Standard message format for all AI providers"""
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[Dict[str, Any]] = None

class AIRequest(BaseModel):
    """Standardized request format"""
    messages: List[AIMessage]
    model_name: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
class AIResponse(BaseModel):
    """Standardized response format"""
    content: str
    provider: ModelProvider
    model_used: str
    usage_stats: Dict[str, int]  # tokens, etc.
    response_time_ms: float
    metadata: Dict[str, Any] = {}

class ClientError(Exception):
    """Base exception for AI client errors"""
    def __init__(self, message: str, provider: ModelProvider, error_code: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code

class BaseAIClient(ABC):
    """
    Abstract base class for all AI provider clients.
    
    Ensures consistent interface across Claude, OpenAI, and Gemini.
    Handles common concerns like rate limiting, retries, and error formatting.
    """
    
    def __init__(self, api_key: str, provider: ModelProvider):
        self.api_key = api_key
        self.provider = provider
        self._rate_limit_delay = 0.1  # Minimum delay between requests
        self._last_request_time = 0.0
        self._request_count = 0
        
    @abstractmethod
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """
        Generate AI response for given request.
        Must be implemented by each provider-specific client.
        """
        pass
    
    @abstractmethod
    def _validate_model(self, model_name: str) -> bool:
        """Validate that the model name is supported by this provider"""
        pass
    
    @abstractmethod
    def _get_default_model(self) -> str:
        """Get the default model for this provider"""
        pass
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - time_since_last)
            
        self._last_request_time = time.time()
        self._request_count += 1
    
    def _prepare_messages(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        """Convert AIMessage objects to provider-specific format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    async def _handle_request_with_retry(
        self, 
        request_func,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ):
        """Generic retry logic with exponential backoff"""
        
        for attempt in range(max_retries + 1):
            try:
                return await request_func()
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"{self.provider.value} client failed after {max_retries} retries: {e}")
                    raise ClientError(
                        f"Request failed after {max_retries} retries: {str(e)}", 
                        self.provider
                    )
                
                wait_time = backoff_factor ** attempt
                logger.warning(f"{self.provider.value} request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client usage statistics"""
        return {
            "provider": self.provider.value,
            "total_requests": self._request_count,
            "last_request_time": self._last_request_time
        }
    
    def _log_request(self, request: AIRequest, response_time_ms: float, success: bool):
        """Log request for monitoring (privacy-safe)"""
        if success:
            logger.info(
                f"{self.provider.value} request completed: "
                f"model={request.model_name}, "
                f"messages={len(request.messages)}, "
                f"time={response_time_ms:.1f}ms"
            )
        else:
            logger.error(f"{self.provider.value} request failed after {response_time_ms:.1f}ms")
