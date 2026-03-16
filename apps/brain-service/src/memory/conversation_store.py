import sqlite3
import json
import logging
import datetime
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# --- IMPORT YOUR EMBEDDING ENGINE ---
from src.rag.embedding_service import EmbeddingService

logger = logging.getLogger("conversation_store")

@dataclass
class Conversation:
    id: int
    user_id: str
    message: str
    role: str
    timestamp: datetime.datetime  # Must be a real datetime object
    conversation_id: str
    conversation_type: str
    similarity_score: float = 0.0

class ConversationStore:
    def __init__(self, embedding_service=None, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.embedding_service = embedding_service or EmbeddingService()
        self.SIMILARITY_THRESHOLD = 0.3 

    async def initialize(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    role TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    conversation_id TEXT,
                    conversation_type TEXT,
                    embedding_vector TEXT
                )
            ''')
            
            # Migration Check
            cursor.execute("PRAGMA table_info(conversations)")
            columns = [info[1] for info in cursor.fetchall()]
            if "embedding_vector" not in columns:
                logger.info("⚡ Migrating Database: Adding embedding_vector column...")
                cursor.execute("ALTER TABLE conversations ADD COLUMN embedding_vector TEXT")
            
            conn.commit()
            conn.close()
            logger.info(f"✅ ConversationStore initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Database Initialization Failed: {e}")
            raise

    async def store_message(self, user_id: str, message: str, role: str, conversation_id: str, conversation_type: str = "chat"):
        try:
            # 1. Generate Semantic Embedding
            embedding = None
            try:
                vector = self.embedding_service.generate_embedding(message)
                if vector:
                    embedding = json.dumps(vector) 
            except Exception as emb_err:
                logger.warning(f"⚠️ Embedding failed: {emb_err}")

            # 2. Save to DB
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations 
                (user_id, message, role, conversation_id, conversation_type, embedding_vector, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, message, role, conversation_id, conversation_type, embedding, datetime.datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to store message: {e}")

    # --- HELPER: Fixes the 'str' object has no attribute 'isoformat' error ---
    def _parse_timestamp(self, ts_str) -> datetime.datetime:
        if isinstance(ts_str, datetime.datetime):
            return ts_str
        try:
            # Try parsing with microseconds
            return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, TypeError):
            try:
                # Try parsing without microseconds
                return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except:
                # If all else fails, return current time to prevent crash
                return datetime.datetime.now()

    async def search_conversations(self, user_id: str, query: str, limit: int = 5) -> List[Conversation]:
        try:
            # 1. Embed Query
            query_vector = self.embedding_service.generate_embedding(query)
            if not query_vector:
                return await self._fallback_text_search(user_id, query, limit)

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 2. Fetch Data
            cursor.execute('''
                SELECT * FROM conversations 
                WHERE user_id = ? AND embedding_vector IS NOT NULL
                ORDER BY id DESC LIMIT 100 
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return []

            # 3. Calculate Similarity
            results = []
            q_vec = np.array(query_vector)
            norm_q = np.linalg.norm(q_vec)

            for row in rows:
                try:
                    db_vec = np.array(json.loads(row['embedding_vector']))
                    norm_db = np.linalg.norm(db_vec)
                    
                    if norm_q > 0 and norm_db > 0:
                        score = np.dot(q_vec, db_vec) / (norm_q * norm_db)
                    else:
                        score = 0.0

                    if score >= self.SIMILARITY_THRESHOLD:
                        results.append((score, row))
                except Exception:
                    continue

            # 4. Sort and Convert
            results.sort(key=lambda x: x[0], reverse=True)

            top_results = []
            for score, row in results[:limit]:
                # FIX IS APPLIED HERE: _parse_timestamp
                top_results.append(Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    message=row['message'],
                    role=row['role'],
                    timestamp=self._parse_timestamp(row['timestamp']), 
                    conversation_id=row['conversation_id'],
                    conversation_type=row['conversation_type'],
                    similarity_score=score
                ))

            return top_results

        except Exception as e:
            logger.error(f"❌ Semantic Search Failed: {e}")
            return await self._fallback_text_search(user_id, query, limit)

    async def _fallback_text_search(self, user_id: str, query: str, limit: int) -> List[Conversation]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM conversations 
            WHERE user_id = ? AND message LIKE ? 
            ORDER BY id DESC LIMIT ?
        ''', (user_id, f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # FIX IS APPLIED HERE TOO
        return [Conversation(
            id=r['id'], 
            user_id=r['user_id'], 
            message=r['message'], 
            role=r['role'], 
            timestamp=self._parse_timestamp(r['timestamp']), 
            conversation_id=r['conversation_id'], 
            conversation_type=r['conversation_type']
        ) for r in rows]