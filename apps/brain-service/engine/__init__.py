"""
Identra Brain Service - Engine Package
Owner: Sailesh

This package contains the core RAG processing modules:
- extractor: Signal extraction from user messages
- memory_client: gRPC client for vault-daemon communication  
- memory_selector: Memory selection logic (TODO)
- context_pack: Context pack building for LLM prompts (TODO)
"""

from .memory_client import MemoryClient, MemoryItem, get_memory_client

__all__ = [
    "MemoryClient", 
    "MemoryItem",
    "get_memory_client"
]