"""
Identra Brain Service - FastAPI RAG Orchestration
Owner: Sailesh

This service receives requests from tunnel-gateway and orchestrates:
1. Signal extraction from user messages
2. Memory retrieval from vault-daemon (via gRPC) 
3. Context pack building for AI responses
4. RAG processing and inference

Architecture: tunnel-gateway → brain-service → vault-daemon
Communication: All via gRPC using identra-proto definitions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import uuid
import os
from contextlib import asynccontextmanager

# Import our adapted engine modules  
from engine.extractor import extract_signals
from engine.memory_client import get_memory_client, MemoryClient, MemoryItem
# from engine.memory_selector import select_memory  # TODO: Implement
# from engine.context_pack import build_context_pack  # TODO: Implement

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("identra.brain")

# Memory client will be initialized on startup
memory_client: Optional[MemoryClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events."""
    global memory_client
    
    # Startup
    logger.info("🧠 Identra Brain Service starting up...")
    
    # Initialize gRPC connection to vault-daemon
    memory_client = await get_memory_client()
    
    # Attempt to connect to vault-daemon
    vault_address = os.getenv("VAULT_DAEMON_ADDRESS", "localhost:50051")
    memory_client.vault_daemon_address = vault_address
    
    connected = await memory_client.connect()
    if connected:
        logger.info(f"✅ Memory client connected to vault-daemon at {vault_address}")
    else:
        logger.warning(f"⚠️ Memory client failed to connect to vault-daemon at {vault_address} - continuing in mock mode")
    
    logger.info("✅ Brain Service ready!")
    
    yield  # This is where the application runs
    
    # Shutdown
    logger.info("🛑 Identra Brain Service shutting down...")
    
    # Close gRPC connections
    if memory_client:
        await memory_client.disconnect()
    
    logger.info("✅ Brain Service stopped!")

# Initialize FastAPI app with lifespan manager
app = FastAPI(
    title="Identra Brain Service", 
    description="RAG orchestration service - receives from tunnel-gateway, queries vault-daemon",
    version="0.1.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan
)

# ---------- Request Models ----------

class ContextRequest(BaseModel):
    """Request model for low-level context pack building."""
    topic: str
    text_blocks: List[str]
    usage_instruction: str
    entity: Optional[str] = "general"


class IdentraRequest(BaseModel):
    """
    Main request model - matches what tunnel-gateway sends.
    This follows the actual Identra request flow.
    """
    user_message: str
    conversation_id: str  # From tunnel-gateway (maps to sessions)
    user_id: Optional[str] = None  # For user-specific memory retrieval
    model_preferences: Optional[Dict[str, Any]] = None  # LLM model settings
    context_limit: int = 10  # Max memories to retrieve


class MemoryQueryRequest(BaseModel):
    """Request model for memory queries."""
    entity: Optional[str] = None
    topic: Optional[str] = None
    limit: int = 10
    include_context: bool = True


# ---------- Response Models ----------

class SignalsResponse(BaseModel):
    """Response model for extracted signals."""
    entity: str
    topic: str
    usage_instruction: str
    confidence_score: float
    text_blocks: List[str]


class MemoryItem(BaseModel):
    """
    Memory item - matches identra-proto Memory message structure.
    This aligns with libs/identra-proto/proto/memory.proto
    """
    id: str
    content: str
    metadata: Dict[str, str]  # Contains entity, topic, etc.
    similarity_score: Optional[float] = None  # From vector search
    created_at: datetime
    tags: List[str] = []


class IdentraResponse(BaseModel):
    """
    Main response model - sent back to tunnel-gateway.
    Contains enhanced prompt for LLM with retrieved context.
    """
    enhanced_prompt: str  # Final prompt with context for LLM
    retrieved_memories: List[MemoryItem]  # Relevant memories found
    signals: SignalsResponse  # Extracted conversation signals
    processing_metadata: Dict  # Stats, timing, confidence scores


# ---------- Health Check ----------

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "identra-brain-service",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# ---------- Signal Extraction Endpoint ----------

@app.post("/extract-signals", response_model=SignalsResponse)
async def extract_conversation_signals(request: IdentraRequest):
    """
    Extract conversation signals from user message.
    Useful for testing and debugging the extractor.
    """
    try:
        signals = extract_signals(request.user_message)
        
        return SignalsResponse(
            entity=signals["entity"],
            topic=signals["topic"], 
            usage_instruction=signals["usage_instruction"],
            confidence_score=signals["confidence_score"],
            text_blocks=signals["text_blocks"]
        )
    except Exception as e:
        logger.error(f"Signal extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Signal extraction failed: {str(e)}")


# ---------- Main RAG Orchestration Endpoint ----------

@app.post("/identra/process", response_model=IdentraResponse)
async def process_conversation(request: IdentraRequest):
    """
    Main RAG orchestration endpoint - called by tunnel-gateway.
    
    Identra Flow:
    1. tunnel-gateway receives user message from desktop app
    2. tunnel-gateway calls this endpoint with user_message + conversation_id  
    3. brain-service extracts signals and queries vault-daemon for memories
    4. brain-service builds enhanced prompt with retrieved context
    5. tunnel-gateway receives enhanced_prompt and sends to LLM
    6. LLM response flows back to desktop app
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Processing conversation {request.conversation_id}: {request.user_message[:100]}...")
        
        # Step 1: Extract conversation signals
        signals = extract_signals(request.user_message)
        logger.info(f"Extracted signals - entity: {signals['entity']}, topic: {signals['topic']}")
        
        # Step 2: Query relevant memories from vault-daemon via gRPC
        retrieved_memories = []
        try:
            if memory_client and await memory_client.health_check():
                # Query memories using the memory client
                filters = {
                    "entity": signals["entity"],
                    "topic": signals["topic"],
                    "user_id": request.user_id or "default"
                }
                
                client_memories = await memory_client.query_memories(
                    query=request.user_message,
                    limit=request.context_limit,
                    filters=filters
                )
                
                # Convert MemoryClient items to our response format
                retrieved_memories = [
                    MemoryItem(
                        id=mem.id,
                        content=mem.content,
                        metadata=mem.metadata,
                        similarity_score=mem.similarity_score,
                        created_at=mem.created_at,
                        tags=mem.tags
                    ) for mem in client_memories
                ]
                
                logger.info(f"✅ Retrieved {len(retrieved_memories)} memories via gRPC")
            else:
                logger.warning("Memory client not available or unhealthy - continuing without context")
            
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}, continuing without context")
        
        # Step 3: Build enhanced prompt with retrieved context  
        enhanced_prompt = _build_enhanced_prompt(
            user_message=request.user_message,
            signals=signals,
            memories=retrieved_memories
        )
        
        # Step 4: Store this conversation in vault-daemon for future retrieval
        try:
            if memory_client and await memory_client.health_check():
                # Store the current conversation as a new memory
                memory_metadata = {
                    "entity": signals["entity"],
                    "topic": signals["topic"],
                    "conversation_id": request.conversation_id,
                    "user_id": request.user_id or "default",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                memory_id = await memory_client.store_memory(
                    content=request.user_message,
                    metadata=memory_metadata,
                    tags=[signals["entity"], signals["topic"]]
                )
                
                if memory_id:
                    logger.info(f"✅ Stored conversation memory with ID: {memory_id}")
                else:
                    logger.warning("Memory storage returned no ID")
            else:
                logger.warning("Memory client not available - memory not stored")
            
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")
        
        # Step 5: Calculate processing metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Determine vault communication status
        vault_status = "disconnected"
        if memory_client:
            if await memory_client.health_check():
                vault_status = "connected"
            else:
                vault_status = "mock_mode"
                
        return IdentraResponse(
            enhanced_prompt=enhanced_prompt,
            retrieved_memories=retrieved_memories,
            signals=SignalsResponse(
                entity=signals["entity"],
                topic=signals["topic"],
                usage_instruction=signals["usage_instruction"],
                confidence_score=signals["confidence_score"], 
                text_blocks=signals["text_blocks"]
            ),
            processing_metadata={
                "processing_time_ms": processing_time,
                "memories_retrieved": len(retrieved_memories),
                "confidence_score": signals["confidence_score"],
                "conversation_id": request.conversation_id,
                "vault_communication": vault_status
            }
        )
        
    except Exception as e:
        logger.error(f"RAG processing failed for conversation {request.conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG processing failed: {str(e)}")


def _build_enhanced_prompt(user_message: str, signals: dict, memories: List[MemoryItem]) -> str:
    """
    Build enhanced prompt with retrieved context for the LLM.
    This is the core RAG functionality.
    """
    if not memories:
        return user_message  # No context available
    
    # Build context section from retrieved memories
    context_section = "## Relevant Context from Previous Conversations:\n\n"
    for memory in memories:
        context_section += f"- {memory.content}\n"
        if memory.metadata.get("timestamp"):
            context_section += f"  (From: {memory.metadata['timestamp']})\n"
    
    # Build enhanced prompt
    enhanced_prompt = f"""You are an AI assistant with access to the user's conversation history.

{context_section}

## Current Request:
{user_message}

## Instructions:
- Use the context above to provide relevant and personalized responses
- Reference previous conversations when appropriate
- If the context is not relevant to the current request, focus on the current request
- Be conversational and maintain continuity with previous interactions"""
    
    return enhanced_prompt


# ---------- Memory Query Endpoints ----------

@app.post("/identra/memory/query")
async def query_memories(request: MemoryQueryRequest):
    """
    Query memories by entity, topic, or other criteria.
    """
    try:
        memories = []
        
        if memory_client and await memory_client.health_check():
            # Build filters from request parameters
            filters = {}
            if request.entity:
                filters["entity"] = request.entity
            if request.topic:
                filters["topic"] = request.topic
                
            # Use a generic query or get recent memories if no specific query
            if request.entity or request.topic:
                query = f"{request.entity or ''} {request.topic or ''}".strip()
                client_memories = await memory_client.query_memories(
                    query=query,
                    limit=request.limit,
                    filters=filters
                )
            else:
                # Get recent memories if no specific filters
                client_memories = await memory_client.get_recent_memories(limit=request.limit)
            
            # Convert to response format
            memories = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "metadata": mem.metadata,
                    "created_at": mem.created_at.isoformat(),
                    "tags": mem.tags,
                    "similarity_score": mem.similarity_score
                } for mem in client_memories
            ]
            
            logger.info(f"✅ Queried {len(memories)} memories - entity: {request.entity}, topic: {request.topic}")
        else:
            logger.warning("Memory client not available for query")
        
        return {
            "memories": memories,
            "total_count": len(memories),
            "query_params": {
                "entity": request.entity,
                "topic": request.topic,
                "limit": request.limit
            }
        }
    except Exception as e:
        logger.error(f"Memory query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")


@app.get("/identra/memory/entities")
async def get_all_entities():
    """
    Get list of all entities currently stored in memory.
    """
    try:
        # TODO: Implement when memory_client is ready
        # entities = await memory_client.get_all_entities()
        
        # Stubbed response
        entities = []
        logger.info("Entity listing stubbed")
        
        return {
            "entities": entities,
            "total_count": len(entities)
        }
    except Exception as e:
        logger.error(f"Entity listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Entity listing failed: {str(e)}")


@app.get("/identra/memory/topics")
async def get_all_topics():
    """
    Get list of all topics currently stored in memory.
    """
    try:
        # TODO: Implement when memory_client is ready
        # topics = await memory_client.get_all_topics()
        
        # Stubbed response
        topics = []
        logger.info("Topic listing stubbed")
        
        return {
            "topics": topics,
            "total_count": len(topics)
        }
    except Exception as e:
        logger.error(f"Topic listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Topic listing failed: {str(e)}")


# ---------- Legacy Compatibility Endpoint ----------

@app.post("/build-context")
async def build_context_legacy(request: ContextRequest):
    """
    Legacy endpoint for building context packs from explicit inputs.
    Maintained for backward compatibility.
    """
    try:
        # TODO: Implement when context_pack module is ready
        # context_pack = build_context_pack(
        #     topic=request.topic,
        #     text_blocks=request.text_blocks,
        #     usage_instruction=request.usage_instruction,
        #     entity=request.entity
        # )
        
        # Stubbed response
        context_pack = {
            "topic": request.topic,
            "entity": request.entity,
            "text_blocks": request.text_blocks,
            "usage_instruction": request.usage_instruction,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Legacy context pack built for topic: {request.topic}")
        return context_pack
        
    except Exception as e:
        logger.error(f"Legacy context building failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Context building failed: {str(e)}")


# ---------- Development/Debug Endpoints ----------

@app.get("/debug/info")
async def debug_info():
    """Debug information about the service state."""
    return {
        "service": "identra-brain-service",
        "status": "running",
        "modules_loaded": {
            "extractor": True,
            "memory_client": memory_client is not None and memory_client.connected,
            "memory_selector": False,  # TODO
            "context_pack": False      # TODO
        },
        "endpoints_active": [
            "/health",
            "/extract-signals", 
            "/identra/process",
            "/identra/memory/query",
            "/identra/memory/entities",
            "/identra/memory/topics",
            "/build-context"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
