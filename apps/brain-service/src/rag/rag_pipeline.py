"""
Identra RAG Pipeline
Connects Retriever → Augmentor → Generator into one flow.
"""
import logging
from typing import List, Dict, Any
from .retriever import RAGRetriever
from .augmentor import RAGAugmentor

logger = logging.getLogger("rag_pipeline")

class RAGPipeline:
    def __init__(self, db_path: str = "conversations.db", embedding_service=None):
        self.retriever = RAGRetriever(db_path=db_path, embedding_service=embedding_service)
        self.augmentor = RAGAugmentor()
        logger.info("✅ RAG Pipeline ready")

    def process(self, query: str, user_id: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Full RAG flow:
        1. RETRIEVE similar memories
        2. AUGMENT query with context
        3. Return augmented prompt + metadata

        Returns:
            {
                "augmented_prompt": str,
                "memories_used": int,
                "retrieved_memories": list
            }
        """
        try:
            # 1. RETRIEVE
            logger.info(f"🔍 Retrieving memories for: '{query[:50]}'")
            memories = self.retriever.retrieve(
                query=query,
                user_id=user_id,
                top_k=top_k
            )

            # 2. AUGMENT
            augmented_prompt = self.augmentor.augment(
                query=query,
                memories=memories
            )

            logger.info(f"🧠 RAG Pipeline complete — {len(memories)} memories used")

            return {
                "augmented_prompt": augmented_prompt,
                "memories_used": len(memories),
                "retrieved_memories": memories
            }

        except Exception as e:
            logger.error(f"❌ RAG Pipeline failed: {e}")
            return {
                "augmented_prompt": query,
                "memories_used": 0,
                "retrieved_memories": []
            }
