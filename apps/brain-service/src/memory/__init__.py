"""
Identra Memory Management Module

Core memory and conversation storage for RAG-powered context retrieval.
Handles conversation persistence, indexing, and retrieval for the brain-service.
"""

from .conversation_store import ConversationStore, ConversationRecord, StorageConfig

__all__ = [
    "ConversationStore",
    "ConversationRecord", 
    "StorageConfig"
]
