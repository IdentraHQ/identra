"""
HuggingFace API Client - Free AI Integration for Identra
"""

import time
import logging
from typing import Dict, List, Optional, Any

from huggingface_hub import InferenceClient

from .base_client import BaseAIClient, AIRequest, AIResponse, AIMessage, ModelProvider, ClientError

logger = logging.getLogger("huggingface_client")


class HuggingFaceClient(BaseAIClient):
    """
    HuggingFace Inference API client - FREE tier for Identra development.
    """

    HF_MODELS = {
        "Qwen/Qwen2.5-7B-Instruct": {
            "max_tokens": 4096,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "strengths": ["free", "general", "chat"],
        },
        "mistralai/Mistral-7B-Instruct-v0.2": {
            "max_tokens": 4096,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "strengths": ["free", "chat", "instructions"],
        },
    }

    def __init__(self, api_key: str):
        super().__init__(api_key, ModelProvider.HUGGINGFACE)
        self.client = InferenceClient(api_key=api_key)
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def generate_response(self, request: AIRequest) -> AIResponse:
        start_time = time.time()

        model_name = request.model_name or "mistralai/Mistral-7B-Instruct-v0.2"

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        try:
            result = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=request.max_tokens or 512,
                temperature=request.temperature or 0.7,
            )

            content = result.choices[0].message.content.strip()
            response_time_ms = (time.time() - start_time) * 1000

            return AIResponse(
                content=content,
                provider=ModelProvider.HUGGINGFACE,
                model_used=model_name,
                usage_stats={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                response_time_ms=response_time_ms,
                metadata={"finish_reason": result.choices[0].finish_reason},
            )

        except Exception as e:
            raise ClientError(f"HuggingFace error: {str(e)}", ModelProvider.HUGGINGFACE, "api_error")

    def _validate_model(self, model_name: str) -> bool:
        return model_name in self.HF_MODELS

    def _get_default_model(self) -> str:
        return "Qwen/Qwen2.5-7B-Instruct"

    def get_available_models(self) -> List[str]:
        return list(self.HF_MODELS.keys())

    def get_usage_summary(self) -> Dict[str, Any]:
        return {
            "provider": "huggingface",
            "total_requests": self._request_count,
            "available_models": list(self.HF_MODELS.keys()),
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
            logger.error(f"HuggingFace health check failed: {e}")
            return False
