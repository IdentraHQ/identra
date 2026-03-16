"""
Identra AI Module

Multi-model AI routing, summarization, and external API integrations.
"""

try:
    from .summarizer_service import SummarizerService, SummarizationRequest, SummarizationResponse
except ImportError:
    SummarizerService = None
    SummarizationRequest = None
    SummarizationResponse = None

from .model_router import ModelRouter, ModelRoutingDecision

__all__ = [
    "SummarizerService",
    "SummarizationRequest",
    "SummarizationResponse",
    "ModelRouter",
    "ModelRoutingDecision"
]