"""
Identra RAG Retriever
Searches SQLite for semantically similar past conversations.
"""
import sqlite3
import json
import logging
import numpy as np
from typing import List, Dict, Any
from .embedding_service import EmbeddingService

logger = logging.getLogger("rag_retriever")

class RAGRetriever:
    def __init__(self, db_path: str = "conversations.db", embedding_service=None):
        self.db_path = db_path
        self.embedding_service = embedding_service or EmbeddingService()
        self.SIMILARITY_THRESHOLD = 0.3

    def retrieve(self, query: str, user_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find top-k most relevant past conversations for a query."""
        try:
            # 1. Embed the query
            query_vector = self.embedding_service.generate_embedding(query)
            if not query_vector:
                return []

            # 2. Fetch all stored memories
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM conversations
                WHERE user_id = ? AND embedding_vector IS NOT NULL
                ORDER BY id DESC LIMIT 100
            ''', (user_id,))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return []

            # 3. Calculate similarity scores
            q_vec = np.array(query_vector)
            results = []

            for row in rows:
                try:
                    db_vec = np.array(json.loads(row['embedding_vector']))
                    norm_q = np.linalg.norm(q_vec)
                    norm_db = np.linalg.norm(db_vec)

                    if norm_q > 0 and norm_db > 0:
                        score = float(np.dot(q_vec, db_vec) / (norm_q * norm_db))
                    else:
                        score = 0.0

                    if score >= self.SIMILARITY_THRESHOLD:
                        results.append({
                            "message": row['message'],
                            "role": row['role'],
                            "score": round(score, 4),
                            "conversation_id": row['conversation_id'],
                            "timestamp": row['timestamp']
                        })
                except Exception:
                    continue

            # 4. Sort by score and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            top_results = results[:top_k]

            logger.info(f"✅ Retrieved {len(top_results)} relevant memories for query")
            return top_results

        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []
