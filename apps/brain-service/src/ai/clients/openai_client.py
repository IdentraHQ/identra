"""
OpenAI API Client - GPT Integration

Handles communication with OpenAI's GPT API.
Provides standardized integration with proper error handling and rate limiting.
"""

import time
import logging
from typing import Dict, List, Optional, Any

from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIError

from .base_client import BaseAIClient, AIRequest, AIResponse, AIMessage, ModelProvider, ClientError

logger = logging.getLogger("openai_client")


class OpenAIClient(BaseAIClient):
    """
    OpenAI GPT client with full async support.

    Features:
    - GPT-4o / GPT-3.5-turbo support
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Fallback model selection
    """

    OPENAI_MODELS = {
        "gpt-4o": {
            "max_tokens": 128000,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "strengths": ["coding", "reasoning", "creative_writing"],
        },
        "gpt-4o-mini": {
            "max_tokens": 128000,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
            "strengths": ["speed", "simple_tasks"],
        },
        "gpt-3.5-turbo": {
            "max_tokens": 16385,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
            "strengths": ["speed", "casual", "low_cost"],
        },
    }

    def __init__(self, api_key: str):
        super().__init__(api_key, ModelProvider.OPENAI)
        self.client = AsyncOpenAI(api_key=api_key, timeout=60.0)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    async def generate_response(self, request: AIRequest) -> AIResponse:
        start_time = time.time()

        if not self._validate_model(request.model_name):
            request.model_name = self._get_default_model()
            logger.warning(f"Invalid OpenAI model, using default: {request.model_name}")

        await self._enforce_rate_limit()

        openai_messages = self._convert_to_openai_format(request.messages)

        try:
            response = await self._handle_request_with_retry(
                lambda: self.client.chat.completions.create(
                    model=request.model_name,
                    messages=openai_messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens or 4096,
                )
            )

            response_time_ms = (time.time() - start_time) * 1000

            content = response.choices[0].message.content or ""
            usage_stats = self._extract_usage_stats(response)
            self._update_usage_tracking(usage_stats, request.model_name)

            return AIResponse(
                content=content,
                provider=ModelProvider.OPENAI,
                model_used=request.model_name,
                usage_stats=usage_stats,
                response_time_ms=response_time_ms,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "estimated_cost": self._calculate_request_cost(usage_stats, request.model_name),
                },
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            raise self._convert_to_client_error(e)

    def _convert_to_openai_format(self, messages: List[AIMessage]) -> List[Dict[str, str]]:
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _extract_usage_stats(self, response) -> Dict[str, int]:
        usage = getattr(response, "usage", None)
        if usage:
            return {
                "input_tokens": getattr(usage, "prompt_tokens", 0),
                "output_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _update_usage_tracking(self, usage_stats: Dict[str, int], model: str):
        self.total_input_tokens += usage_stats.get("input_tokens", 0)
        self.total_output_tokens += usage_stats.get("output_tokens", 0)
        model_info = self.OPENAI_MODELS.get(model, {})
        cost = (
            (usage_stats.get("input_tokens", 0) / 1000) * model_info.get("cost_per_1k_input", 0)
            + (usage_stats.get("output_tokens", 0) / 1000) * model_info.get("cost_per_1k_output", 0)
        )
        self.total_cost += cost

    def _calculate_request_cost(self, usage_stats: Dict[str, int], model: str) -> float:
        model_info = self.OPENAI_MODELS.get(model, {})
        return (
            (usage_stats.get("input_tokens", 0) / 1000) * model_info.get("cost_per_1k_input", 0)
            + (usage_stats.get("output_tokens", 0) / 1000) * model_info.get("cost_per_1k_output", 0)
        )

    def _convert_to_client_error(self, error: Exception) -> ClientError:
        if isinstance(error, RateLimitError):
            return ClientError("OpenAI rate limit exceeded. Please wait.", ModelProvider.OPENAI, "rate_limit")
        elif isinstance(error, APITimeoutError):
            return ClientError("OpenAI request timed out.", ModelProvider.OPENAI, "timeout")
        elif isinstance(error, APIError):
            return ClientError(f"OpenAI API error: {str(error)}", ModelProvider.OPENAI, "api_error")
        else:
            return ClientError(f"Unexpected OpenAI error: {str(error)}", ModelProvider.OPENAI, "unknown")

    def _validate_model(self, model_name: str) -> bool:
        return model_name in self.OPENAI_MODELS

    def _get_default_model(self) -> str:
        return "gpt-4o-mini"

    def get_available_models(self) -> List[str]:
        return list(self.OPENAI_MODELS.keys())

    def get_usage_summary(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "total_requests": self._request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "available_models": list(self.OPENAI_MODELS.keys()),
        }

    async def health_check(self) -> bool:
        try:
            test_request = AIRequest(
                messages=[AIMessage(role="user", content="Hello")],
                model_name=self._get_default_model(),
                max_tokens=10,
            )
            await self.generate_response(test_request)
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
