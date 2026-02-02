"""
Identra Brain Service - Memory Client
Owner: Sailesh

gRPC client for communicating with vault-daemon MemoryService.
This client handles all memory operations for the RAG system:
- Store conversation memories
- Query memories by similarity/metadata
- Retrieve recent memories for context

Architecture: brain-service (this client) → gRPC → vault-daemon
Protocol: Uses identra-proto/proto/memory.proto definitions
"""

import grpc
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from dataclasses import dataclass

# Import generated gRPC stubs
try:
    # Import the generated protobuf and gRPC stubs
    from identra_proto import (
        Memory, MemoryMatch,
        StoreMemoryRequest, StoreMemoryResponse,
        QueryMemoriesRequest, QueryMemoriesResponse, 
        SearchMemoriesRequest, SearchMemoriesResponse,
        GetRecentMemoriesRequest, GetRecentMemoriesResponse,
        MemoryServiceStub
    )
    PROTO_AVAILABLE = True
except ImportError as e:
    # Fallback for development without generated protos
    PROTO_AVAILABLE = False
    print(f"Warning: identra-proto gRPC stubs not available: {e}. Memory client will use mock responses.")

logger = logging.getLogger("identra.brain.memory_client")


@dataclass 
class MemoryItem:
    """Memory item data structure matching the proto Memory message."""
    id: str
    content: str
    metadata: Dict[str, str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[str] = None
    similarity_score: Optional[float] = None  # Added during search operations
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryClient:
    """
    Async gRPC client for vault-daemon MemoryService.
    
    Handles all memory operations for the brain service RAG system:
    - store_memory(): Store new conversation memories
    - query_memories(): Semantic search for relevant memories  
    - get_recent_memories(): Fetch recent conversation history
    - search_memories(): Vector similarity search with custom embeddings
    """
    
    def __init__(self, vault_daemon_address: str = "localhost:50051"):
        """
        Initialize memory client.
        
        Args:
            vault_daemon_address: Address of vault-daemon gRPC server
        """
        self.vault_daemon_address = vault_daemon_address
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[Any] = None
        self.connected = False
        
    async def connect(self) -> bool:
        """
        Establish gRPC connection to vault-daemon.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not PROTO_AVAILABLE:
                logger.warning("gRPC proto stubs not available - using mock client")
                self.connected = True
                return True
                
            # Create async gRPC channel
            self.channel = grpc.aio.insecure_channel(self.vault_daemon_address)
            
            # Create gRPC stub
            self.stub = MemoryServiceStub(self.channel)
            
            # Wait for the channel to be ready (with timeout)
            try:
                await asyncio.wait_for(
                    self.channel.channel_ready(), 
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                raise Exception(f"Connection timeout to {self.vault_daemon_address}")
                
            self.connected = True
            
            logger.info(f"✅ Memory client connected to vault-daemon at {self.vault_daemon_address}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to vault-daemon: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close gRPC connection."""
        if self.channel:
            await self.channel.close()
            self.connected = False
            logger.info("Memory client disconnected from vault-daemon")
    
    async def store_memory(
        self, 
        content: str,
        metadata: Dict[str, str],
        tags: List[str] = None
    ) -> Optional[str]:
        """
        Store a new memory in vault-daemon.
        
        Args:
            content: The memory content (user message, conversation snippet, etc.)
            metadata: Key-value metadata (entity, topic, user_id, conversation_id, etc.) 
            tags: List of tags for categorization
            
        Returns:
            str: Memory ID if successful, None if failed
        """
        if not self.connected:
            logger.error("Memory client not connected - call connect() first")
            return None
            
        try:
            if not PROTO_AVAILABLE:
                # Mock response for development
                mock_id = f"mock_memory_{datetime.utcnow().timestamp()}"
                logger.info(f"MOCK: Stored memory '{content[:50]}...' with ID {mock_id}")
                return mock_id
                
            # Create gRPC request
            request = StoreMemoryRequest(
                content=content,
                metadata=metadata or {},
                tags=tags or []
            )
            
            # Make gRPC call
            response: StoreMemoryResponse = await self.stub.StoreMemory(request)
            
            if response.success:
                logger.info(f"✅ Stored memory with ID: {response.memory_id}")
                return response.memory_id
            else:
                logger.error(f"❌ Memory storage failed: {response.message}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Memory storage error: {e}")
            return None
    
    async def query_memories(
        self,
        query: str,
        limit: int = 10,
        filters: Dict[str, str] = None
    ) -> List[MemoryItem]:
        """
        Query memories using semantic search.
        
        Args:
            query: Search query (user message or keywords)
            limit: Maximum number of memories to return
            filters: Metadata filters (entity, topic, user_id, etc.)
            
        Returns:
            List[MemoryItem]: List of relevant memories
        """
        if not self.connected:
            logger.error("Memory client not connected - call connect() first") 
            return []
            
        try:
            if not PROTO_AVAILABLE:
                # Mock response for development
                logger.info(f"MOCK: Querying memories for '{query}' with filters {filters}")
                return []
                
            # Create gRPC request
            request = QueryMemoriesRequest(
                query=query,
                limit=limit,
                filters=filters or {}
            )
            
            # Make gRPC call
            response: QueryMemoriesResponse = await self.stub.QueryMemories(request)
            
            # Convert proto memories to MemoryItem objects
            memories = []
            for proto_memory in response.memories:
                memory = MemoryItem(
                    id=proto_memory.id,
                    content=proto_memory.content,
                    metadata=dict(proto_memory.metadata),
                    created_at=datetime.fromtimestamp(proto_memory.created_at.seconds),
                    updated_at=datetime.fromtimestamp(proto_memory.updated_at.seconds) if proto_memory.updated_at.seconds else None,
                    tags=list(proto_memory.tags)
                )
                memories.append(memory)
                
            logger.info(f"✅ Retrieved {len(memories)} memories for query: {query}")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Memory query error: {e}")
            return []
    
    async def search_memories(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filters: Dict[str, str] = None
    ) -> List[MemoryItem]:
        """
        Search memories using vector similarity with custom embeddings.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            filters: Metadata filters
            
        Returns:
            List[MemoryItem]: List of similar memories with similarity scores
        """
        if not self.connected:
            logger.error("Memory client not connected - call connect() first")
            return []
            
        try:
            if not PROTO_AVAILABLE:
                # Mock response for development
                logger.info(f"MOCK: Vector search with {len(query_embedding)} dim embedding")
                return []
                
            # Create gRPC request
            request = SearchMemoriesRequest(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold,
                filters=filters or {}
            )
            
            # Make gRPC call
            response: SearchMemoriesResponse = await self.stub.SearchMemories(request)
            
            # Convert proto matches to MemoryItem objects with similarity scores
            memories = []
            for match in response.matches:
                memory = MemoryItem(
                    id=match.memory.id,
                    content=match.memory.content,
                    metadata=dict(match.memory.metadata),
                    created_at=datetime.fromtimestamp(match.memory.created_at.seconds),
                    updated_at=datetime.fromtimestamp(match.memory.updated_at.seconds) if match.memory.updated_at.seconds else None,
                    tags=list(match.memory.tags),
                    similarity_score=match.similarity_score
                )
                memories.append(memory)
                
            logger.info(f"✅ Found {len(memories)} similar memories (threshold: {similarity_threshold})")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Memory search error: {e}")
            return []
    
    async def get_recent_memories(self, limit: int = 20) -> List[MemoryItem]:
        """
        Get recent memories ordered by creation time.
        
        Args:
            limit: Maximum number of recent memories
            
        Returns:
            List[MemoryItem]: List of recent memories
        """
        if not self.connected:
            logger.error("Memory client not connected - call connect() first")
            return []
            
        try:
            if not PROTO_AVAILABLE:
                # Mock response for development
                logger.info(f"MOCK: Getting {limit} recent memories")
                return []
                
            # Create gRPC request
            request = GetRecentMemoriesRequest(limit=limit)
            
            # Make gRPC call
            response: GetRecentMemoriesResponse = await self.stub.GetRecentMemories(request)
            
            # Convert proto memories to MemoryItem objects
            memories = []
            for proto_memory in response.memories:
                memory = MemoryItem(
                    id=proto_memory.id,
                    content=proto_memory.content,
                    metadata=dict(proto_memory.metadata),
                    created_at=datetime.fromtimestamp(proto_memory.created_at.seconds),
                    updated_at=datetime.fromtimestamp(proto_memory.updated_at.seconds) if proto_memory.updated_at.seconds else None,
                    tags=list(proto_memory.tags)
                )
                memories.append(memory)
                
            logger.info(f"✅ Retrieved {len(memories)} recent memories")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Recent memories error: {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check if vault-daemon MemoryService is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not self.connected:
            return False
            
        try:
            if not PROTO_AVAILABLE:
                return True  # Mock healthy for development
                
            # Try a simple operation to check health
            request = GetRecentMemoriesRequest(limit=1)
            await asyncio.wait_for(
                self.stub.GetRecentMemories(request), 
                timeout=5.0
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Memory service health check failed: {e}")
            return False


# Global memory client instance (initialized in main.py startup)
memory_client = MemoryClient()


async def get_memory_client() -> MemoryClient:
    """
    Get the global memory client instance.
    
    Returns:
        MemoryClient: The global memory client
    """
    return memory_client
