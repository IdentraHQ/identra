"""
Identra RAG Augmentor
Injects retrieved memories into the AI prompt as context.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger("rag_augmentor")

class RAGAugmentor:
    def augment(self, query: str, memories: List[Dict[str, Any]]) -> str:
        """
        Builds a context-rich prompt by injecting relevant memories.
        
        Flow:
        memories + query → augmented prompt
        """
        if not memories:
            return query

        # Group memories into user/assistant pairs
        context_parts = []
        context_parts.append("=== RELEVANT PAST CONVERSATIONS ===")

        for mem in memories:
            role = mem.get('role', 'user')
            message = mem.get('message', '')
            score = mem.get('score', 0)

            if role == 'user':
                context_parts.append(f"User previously said: {message}")
            elif role == 'assistant':
                context_parts.append(f"Identra previously responded: {message}")

        context_parts.append("=== END OF CONTEXT ===")
        context_parts.append(f"\nCurrent question: {query}")
        context_parts.append(
            "\nUsing the above context if relevant, provide a helpful response:"
        )

        augmented = "\n".join(context_parts)
        logger.info(f"✅ Augmented prompt with {len(memories)} memories")
        return augmented
