import sqlite3
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Import the Embedding Service (The "Translator" we built earlier)
from src.rag.embedding_service import EmbeddingService

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory_store")

# Database File Name (Created automatically in the root folder)
DB_PATH = "identra_memory.db"

class MemoryStore:
    def __init__(self):
        """
        Initialize the SQLite database and the RAG Embedding Model.
        """
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # 1. Create Tables
        self._init_db()
        
        # 2. Load the RAG Model (This allows us to save vectors)
        logger.info("⏳ Loading Memory RAG Model...")
        self.embedder = EmbeddingService()
        logger.info("✅ Memory Store Online (SQLite + Vectors)")

    def _init_db(self):
        """Creates the necessary database tables if they don't exist."""
        # Table for Conversations (Metadata)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TIMESTAMP,
                title TEXT
            )
        """)
        
        # Table for Messages (Content + Vectors)
        # We store the 384-dimension vector as a text string (JSON) because SQLite is simple.
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                embedding TEXT, 
                timestamp TIMESTAMP
            )
        """)
        self.conn.commit()

    def save_message(self, conversation_id: str, role: str, content: str):
        """
        Saves a message AND its vector embedding to the database.
        """
        try:
            # 1. Convert text to numbers (Vector)
            vector = self.embedder.generate_embedding(content)
            
            # 2. Convert numbers to string (for SQLite storage)
            vector_json = json.dumps(vector) 

            # 3. Save to Database
            self.cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, embedding, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, role, content, vector_json, datetime.now()))
            
            self.conn.commit()
            logger.info(f"💾 Memory Saved: {role} (Vector generated)")
            
        except Exception as e:
            logger.error(f"❌ Failed to save message: {e}")

    def retrieve_context(self, query: str, limit: int = 3) -> List[str]:
        """
        SEMANTIC SEARCH: Finds past messages that mean the same thing as the query.
        """
        try:
            # 1. Vectorize the new question
            query_vector = self.embedder.generate_embedding(query)
            if not query_vector:
                return []

            # 2. Fetch all past messages (In a real app, we'd filter by user_id)
            self.cursor.execute("SELECT content, embedding FROM messages WHERE role != 'system'")
            rows = self.cursor.fetchall()
            
            results = []
            
            # 3. Compare the new vector vs. all old vectors
            for content, emb_json in rows:
                if not emb_json: continue
                
                stored_vector = json.loads(emb_json)
                
                # Math: Calculate Cosine Similarity
                score = self.embedder.calculate_similarity(query_vector, stored_vector)
                
                # Filter: Only keep relevant memories (Score > 0.35)
                if score > 0.35:
                    results.append((score, content))

            # 4. Sort by relevance (Highest score first)
            results.sort(key=lambda x: x[0], reverse=True)
            
            # Return just the text of the top matches
            top_matches = [item[1] for item in results[:limit]]
            
            if top_matches:
                logger.info(f"🔍 Found {len(top_matches)} relevant memories.")
            
            return top_matches

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return []

    def get_recent_history(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Retrieves the last N messages for simple chat context (Short-Term Memory).
        """
        self.cursor.execute("""
            SELECT role, content FROM messages 
            WHERE conversation_id = ? 
            ORDER BY id DESC LIMIT ?
        """, (conversation_id, limit))
        
        rows = self.cursor.fetchall()
        
        # Reverse to get chronological order (Oldest -> Newest)
        history = [{"role": r[0], "content": r[1]} for r in rows][::-1]
        return history