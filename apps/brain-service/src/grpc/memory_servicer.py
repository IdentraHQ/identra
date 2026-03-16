"""
Identra gRPC Memory Servicer
Implements MemoryService for tunnel-gateway communication.
"""
import uuid
import logging
from datetime import datetime

import grpc
from google.protobuf import timestamp_pb2
from generated import memory_pb2, memory_pb2_grpc

from src.memory.conversation_store import ConversationStore
from src.rag.embedding_service import EmbeddingService

logger = logging.getLogger("grpc_memory_servicer")


class MemoryServicer(memory_pb2_grpc.MemoryServiceServicer):
    """
    Implements all 6 gRPC memory methods.
    Connects tunnel-gateway requests to Identra's SQLite memory store.
    """

    def __init__(self, conversation_store: ConversationStore, embedding_service=None):
        self.store = conversation_store
        self.embedding_service = embedding_service or EmbeddingService()
        logger.info("✅ gRPC MemoryServicer initialized")

    def _to_timestamp(self, dt: datetime) -> timestamp_pb2.Timestamp:
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(dt)
        return ts

    def StoreMemory(self, request, context):
        """Store a memory from tunnel-gateway."""
        try:
            memory_id = str(uuid.uuid4())
            user_id = request.metadata.get("user_id", "default")
            session_id = request.metadata.get("session_id", "grpc_session")
            role = request.metadata.get("role", "user")

            import sqlite3
            conn = sqlite3.connect(self.store.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (conversation_id, user_id, message, role) VALUES (?, ?, ?, ?)",
                (session_id, user_id, request.content, role)
            )
            conn.commit()
            conn.close()

            logger.info(f"✅ Stored memory: {memory_id}")
            return memory_pb2.StoreMemoryResponse(
                memory_id=memory_id,
                success=True,
                message="Memory stored successfully"
            )

        except Exception as e:
            logger.error(f"❌ StoreMemory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.StoreMemoryResponse(
                success=False,
                message=str(e)
            )

    def QueryMemories(self, request, context):
        """Query memories by text search."""
        try:
            import sqlite3
            user_id = request.metadata.get("user_id", "default") if hasattr(request, "metadata") else "default"
            limit = request.limit or 5

            conn = sqlite3.connect(self.store.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE user_id = ? AND message LIKE ? ORDER BY id DESC LIMIT ?",
                (user_id, f"%{request.query}%", limit)
            )
            rows = cursor.fetchall()
            conn.close()

            memories = [
                memory_pb2.Memory(
                    id=str(row["id"]),
                    content=row["message"],
                    tags=[row["role"]],
                )
                for row in rows
            ]

            return memory_pb2.QueryMemoriesResponse(
                memories=memories,
                total_count=len(memories)
            )

        except Exception as e:
            logger.error(f"❌ QueryMemories failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.QueryMemoriesResponse(total_count=0)

    def SearchMemories(self, request, context):
        """Search memories by embedding vector."""
        try:
            import asyncio
            import numpy as np
            import json
            import sqlite3

            query_vec = np.array(request.query_embedding)
            threshold = request.similarity_threshold or 0.3
            limit = request.limit or 5

            conn = sqlite3.connect(self.store.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM conversations
                WHERE embedding_vector IS NOT NULL
                ORDER BY id DESC LIMIT 100
            ''')
            rows = cursor.fetchall()
            conn.close()

            matches = []
            for row in rows:
                try:
                    db_vec = np.array(json.loads(row['embedding_vector']))
                    norm_q = np.linalg.norm(query_vec)
                    norm_db = np.linalg.norm(db_vec)
                    if norm_q > 0 and norm_db > 0:
                        score = float(np.dot(query_vec, db_vec) / (norm_q * norm_db))
                        if score >= threshold:
                            mem = memory_pb2.Memory(
                                id=str(row['id']),
                                content=row['message'],
                                tags=[row['role']],
                            )
                            matches.append(memory_pb2.MemoryMatch(
                                memory=mem,
                                similarity_score=score
                            ))
                except Exception:
                    continue

            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            return memory_pb2.SearchMemoriesResponse(matches=matches[:limit])

        except Exception as e:
            logger.error(f"❌ SearchMemories failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.SearchMemoriesResponse()

    def GetMemory(self, request, context):
        """Get a single memory by ID."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.store.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM conversations WHERE id = ?', (request.memory_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Memory not found")
                return memory_pb2.GetMemoryResponse()

            mem = memory_pb2.Memory(
                id=str(row['id']),
                content=row['message'],
                tags=[row['role']],
            )
            return memory_pb2.GetMemoryResponse(memory=mem)

        except Exception as e:
            logger.error(f"❌ GetMemory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.GetMemoryResponse()

    def DeleteMemory(self, request, context):
        """Delete a memory by ID."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.store.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (request.memory_id,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted == 0:
                return memory_pb2.DeleteMemoryResponse(
                    success=False,
                    message="Memory not found"
                )

            return memory_pb2.DeleteMemoryResponse(
                success=True,
                message="Memory deleted successfully"
            )

        except Exception as e:
            logger.error(f"❌ DeleteMemory failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.DeleteMemoryResponse(success=False, message=str(e))

    def GetRecentMemories(self, request, context):
        """Get most recent memories."""
        try:
            import sqlite3
            limit = request.limit or 10
            conn = sqlite3.connect(self.store.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM conversations
                ORDER BY id DESC LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            conn.close()

            memories = [
                memory_pb2.Memory(
                    id=str(row['id']),
                    content=row['message'],
                    tags=[row['role']],
                )
                for row in rows
            ]

            return memory_pb2.GetRecentMemoriesResponse(memories=memories)

        except Exception as e:
            logger.error(f"❌ GetRecentMemories failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return memory_pb2.GetRecentMemoriesResponse()
