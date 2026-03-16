"""
Gemini API Client - Google Integration

Handles communication with Google's Gemini API.
Provides standardized integration with proper error handling and rate limiting.
"""

import time
import logging
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from .base_client import BaseAIClient, AIRequest, AIResponse, AIMessage, ModelProvider, ClientError

logger = logging.getLogger("gemini_client")


class GeminiClient(BaseAIClient):
    """
    Gemini API client with async-compatible support.

    Features:
    - Gemini 1.5 Flash / Pro support
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Fallback model selection
    """

    GEMINI_MODELS = {
        "gemini-1.5-flash": {
            "max_tokens": 1048576,
            "cost_per_1k_input": 0.000075,
            "cost_per_1k_output": 0.0003,
            "strengths": ["speed", "analysis", "research"],
        },
        "gemini-1.5-pro": {
            "max_tokens": 2097152,
            "cost_per_1k_input": 0.00125,
            "cost_per_1k_output": 0.005,
            "strengths": ["complex_reasoning", "long_context", "research"],
        },
        "gemini-2.0-flash-exp": {
            "max_tokens": 1048576,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "strengths": ["speed", "free_tier"],
        },
    }

    def __init__(self, api_key: str):
        super().__init__(api_key, ModelProvider.GEMINI)
        genai.configure(api_key=api_key)
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def _get_model(self, model_name: str) -> genai.GenerativeModel:
        return genai.GenerativeModel(model_name)

    async def generate_response(self, request: AIRequest) -> AIResponse:
        start_time = time.time()

        if not self._validate_model(request.model_name):
            request.model_name = self._get_default_model()
            logger.warning(f"Invalid Gemini model, using default: {request.model_name}")

        await self._enforce_rate_limit()

        model = self._get_model(request.model_name)

        # Build prompt from messages
        prompt = self._build_prompt(request.messages)

        gen_config = GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens or 4096,
        )

        try:
            response = await self._handle_request_with_retry(
                lambda: model.generate_content(prompt, generation_config=gen_config)
            )

            response_time_ms = (time.time() - start_time) * 1000

            content = response.text if response.text else ""

            usage_stats = self._extract_usage_stats(response)
            self._update_usage_tracking(usage_stats, request.model_name)

            return AIResponse(
                content=content,
                provider=ModelProvider.GEMINI,
                model_used=request.model_name,
                usage_stats=usage_stats,
                response_time_ms=response_time_ms,
                metadata={
                    "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else "unknown",
                },
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            raise self._convert_to_client_error(e)

    def _build_prompt(self, messages: List[AIMessage]) -> str:
        """Flatten messages into a single Gemini prompt string."""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"[System]: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
        return "\n".join(parts)

    def _extract_usage_stats(self, response) -> Dict[str, int]:
        try:
            usage = response.usage_metadata
            return {
                "input_tokens": getattr(usage, "prompt_token_count", 0),
                "output_tokens": getattr(usage, "candidates_token_count", 0),
                "total_tokens": getattr(usage, "total_token_count", 0),
            }
        except Exception:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _update_usage_tracking(self, usage_stats: Dict[str, int], model: str):
        self.total_input_tokens += usage_stats.get("input_tokens", 0)
        self.total_output_tokens += usage_stats.get("output_tokens", 0)
        model_info = self.GEMINI_MODELS.get(model, {})
        cost = (
            (usage_stats.get("input_tokens", 0) / 1000) * model_info.get("cost_per_1k_input", 0)
            + (usage_stats.get("output_tokens", 0) / 1000) * model_info.get("cost_per_1k_output", 0)
        )
        self.total_cost += cost

    def _convert_to_client_error(self, error: Exception) -> ClientError:
        msg = str(error).lower()
        if "quota" in msg or "rate" in msg:
            return ClientError("Gemini quota/rate limit exceeded.", ModelProvider.GEMINI, "rate_limit")
        elif "timeout" in msg:
            return ClientError("Gemini request timed out.", ModelProvider.GEMINI, "timeout")
        else:
            return ClientError(f"Gemini error: {str(error)}", ModelProvider.GEMINI, "api_error")

    def _validate_model(self, model_name: str) -> bool:
        return model_name in self.GEMINI_MODELS

    def _get_default_model(self) -> str:
        return "gemini-1.5-flash"

    def get_available_models(self) -> List[str]:
        return list(self.GEMINI_MODELS.keys())

    def get_usage_summary(self) -> Dict[str, Any]:
        return {
            "provider": "gemini",
            "total_requests": self._request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "available_models": list(self.GEMINI_MODELS.keys()),
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
            logger.error(f"Gemini health check failed: {e}")
            return False
