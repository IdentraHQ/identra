"""
External AI Client Module

Provides unified interfaces for Claude, OpenAI GPT, and Google Gemini APIs
with consistent error handling and response formatting.
"""

from .base_client import BaseAIClient, AIResponse, AIRequest, ClientError
from .claude_client import ClaudeClient
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient

__all__ = [
    "BaseAIClient",
    "AIResponse", 
    "AIRequest",
    "ClientError",
    "ClaudeClient",
    "OpenAIClient",
    "GeminiClient"
]
