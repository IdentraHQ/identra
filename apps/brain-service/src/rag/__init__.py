"""
Identra RAG (Retrieval-Augmented Generation) Module

Core RAG functionality for semantic search and context retrieval.
Handles embedding generation, similarity search, and context building for the brain-service.
"""

from .embedding_service import EmbeddingService, EmbeddingConfig, EmbeddingResult

__all__ = [
    "EmbeddingService",
    "EmbeddingConfig", 
    "EmbeddingResult"
]