"""
Claude API Client - Anthropic Integration

Handles communication with Anthropic's Claude API (Claude 3 Sonnet/Haiku/Opus).
Provides privacy-first integration with proper error handling and rate limiting.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
import httpx
from anthropic import AsyncAnthropic, APIError, RateLimitError, APITimeoutError

from .base_client import BaseAIClient, AIRequest, AIResponse, AIMessage, ModelProvider, ClientError

logger = logging.getLogger("claude_client")

class ClaudeClient(BaseAIClient):
    """
    Claude API client with async support and Identra-specific optimizations.
    
    Features:
    - Claude 3 Sonnet/Haiku model support
    - Privacy-preserving request logging
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Context window management (200k tokens)
    """
    
    # Claude model configurations
    CLAUDE_MODELS = {
        "claude-3-sonnet-20240229": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "strengths": ["reasoning", "coding", "analysis"]
        },
        "claude-3-haiku-20240307": {
            "max_tokens": 200000, 
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "strengths": ["speed", "simple_tasks"]
        },
        "claude-3-opus-20240229": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "strengths": ["complex_reasoning", "creative_writing"]
        }
    }
    
    def __init__(self, api_key: str):
        """Initialize Claude client with API key"""
        super().__init__(api_key, ModelProvider.CLAUDE)
        
        # Initialize Anthropic async client
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=60.0  # 60 second timeout for requests
        )
        
        # Usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """
        Generate response using Claude API
        
        Args:
            request: Standardized AI request with messages and parameters
            
        Returns:
            AIResponse: Standardized response with content and metadata
        """
        start_time = time.time()
        
        # Validate model
        if not self._validate_model(request.model_name):
            request.model_name = self._get_default_model()
            logger.warning(f"Invalid Claude model, using default: {request.model_name}")
        
        # Enforce rate limiting
        await self._enforce_rate_limit()
        
        # Prepare Claude-specific message format
        claude_messages = self._convert_to_claude_format(request.messages)
        system_message = self._extract_system_message(request.messages)
        
        try:
            # Make API call with retry logic
            response = await self._handle_request_with_retry(
                lambda: self._make_claude_request(
                    messages=claude_messages,
                    system=system_message,
                    model=request.model_name,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens or 4096
                )
            )
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract response content and usage
            content = response.content[0].text if response.content else ""
            usage_stats = self._extract_usage_stats(response)
            
            # Update tracking
            self._update_usage_tracking(usage_stats, request.model_name)
            
            # Log success (privacy-safe)
            self._log_request(request, response_time_ms, True)
            
            return AIResponse(
                content=content,
                provider=ModelProvider.CLAUDE,
                model_used=request.model_name,
                usage_stats=usage_stats,
                response_time_ms=response_time_ms,
                metadata={
                    "finish_reason": getattr(response, 'stop_reason', 'unknown'),
                    "claude_model_info": self.CLAUDE_MODELS.get(request.model_name, {}),
                    "estimated_cost": self._calculate_request_cost(usage_stats, request.model_name)
                }
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self._log_request(request, response_time_ms, False)
            
            # Convert to standardized error
            raise self._convert_to_client_error(e)
    
    async def _make_claude_request(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int
    ):
        """Make the actual Claude API request"""
        
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add system message if present
        if system:
            request_params["system"] = system
            
        # Claude-specific optimizations for Identra use cases
        if "coding" in str(messages).lower() or "code" in str(messages).lower():
            # Better for code-related queries
            request_params["temperature"] = min(temperature, 0.3)
            
        return await self.client.messages.create(**request_params)
    
    def _convert_to_claude_format(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        """Convert standard messages to Claude format (excludes system messages)"""
        claude_messages = []
        
        for msg in messages:
            if msg.role != "system":  # Claude handles system separately
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
                
        return claude_messages
    
    def _extract_system_message(self, messages: List[AIMessage]) -> Optional[str]:
        """Extract system message for Claude's system parameter"""
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None
    
    def _extract_usage_stats(self, response) -> Dict[str, int]:
        """Extract token usage from Claude response"""
        usage = getattr(response, 'usage', None)
        
        if usage:
            return {
                "input_tokens": getattr(usage, 'input_tokens', 0),
                "output_tokens": getattr(usage, 'output_tokens', 0),
                "total_tokens": getattr(usage, 'input_tokens', 0) + getattr(usage, 'output_tokens', 0)
            }
        else:
            # Fallback estimation if usage not available
            return {
                "input_tokens": 0,
                "output_tokens": 0, 
                "total_tokens": 0
            }
    
    def _update_usage_tracking(self, usage_stats: Dict[str, int], model: str):
        """Update internal usage tracking"""
        self.total_input_tokens += usage_stats.get("input_tokens", 0)
        self.total_output_tokens += usage_stats.get("output_tokens", 0)
        
        # Calculate cost
        model_info = self.CLAUDE_MODELS.get(model, {})
        cost = (
            (usage_stats.get("input_tokens", 0) / 1000) * model_info.get("cost_per_1k_input", 0) +
            (usage_stats.get("output_tokens", 0) / 1000) * model_info.get("cost_per_1k_output", 0)
        )
        self.total_cost += cost
    
    def _calculate_request_cost(self, usage_stats: Dict[str, int], model: str) -> float:
        """Calculate cost for this specific request"""
        model_info = self.CLAUDE_MODELS.get(model, {})
        return (
            (usage_stats.get("input_tokens", 0) / 1000) * model_info.get("cost_per_1k_input", 0) +
            (usage_stats.get("output_tokens", 0) / 1000) * model_info.get("cost_per_1k_output", 0)
        )
    
    def _convert_to_client_error(self, error: Exception) -> ClientError:
        """Convert Anthropic errors to standardized ClientError"""
        
        if isinstance(error, RateLimitError):
            return ClientError(
                "Claude API rate limit exceeded. Please wait before retrying.",
                ModelProvider.CLAUDE,
                "rate_limit"
            )
        elif isinstance(error, APITimeoutError):
            return ClientError(
                "Claude API request timed out. Please try again.",
                ModelProvider.CLAUDE,
                "timeout"
            )
        elif isinstance(error, APIError):
            return ClientError(
                f"Claude API error: {str(error)}",
                ModelProvider.CLAUDE,
                "api_error"
            )
        else:
            return ClientError(
                f"Unexpected Claude client error: {str(error)}",
                ModelProvider.CLAUDE,
                "unknown"
            )
    
    def _validate_model(self, model_name: str) -> bool:
        """Validate Claude model name"""
        return model_name in self.CLAUDE_MODELS
    
    def _get_default_model(self) -> str:
        """Get default Claude model (Sonnet for balanced performance)"""
        return "claude-3-sonnet-20240229"
    
    def get_available_models(self) -> List[str]:
        """Get list of available Claude models"""
        return list(self.CLAUDE_MODELS.keys())
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for monitoring"""
        return {
            "provider": "claude",
            "total_requests": self._request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "available_models": list(self.CLAUDE_MODELS.keys())
        }
    
    async def health_check(self) -> bool:
        """Test Claude API connectivity"""
        try:
            # Simple test request
            test_request = AIRequest(
                messages=[AIMessage(role="user", content="Hello")],
                model_name=self._get_default_model(),
                max_tokens=10
            )
            
            await self.generate_response(test_request)
            return True
            
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False
