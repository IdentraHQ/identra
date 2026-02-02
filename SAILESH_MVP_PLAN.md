# Sailesh's Brain Service MVP Implementation Plan 🧠

**Project**: Identra - Confidential AI Identity & Memory Vault  
**Component**: The Brain Service (Python FastAPI + RAG)  
**Owner**: Sailesh  
**Date**: February 1, 2026  
**Status**: 🔴 Not Started

---

## 📊 Current State Analysis

### Project Overview
**Identra** is a confidential operating system layer that acts as a unified **Identity and Memory Vault** for AI interactions. It solves AI fragmentation by providing a single, secure source of truth across different AI tools.

**Architecture Stack:**
- **The Nexus (Desktop)**: Tauri v2 + Rust (Manish) - System hooks, local state
- **The View (UI)**: React + Vite (OmmPrakash) - WebView frontend
- **The Tunnel (Gateway)**: Rust gRPC service (Sarthak) - External communication
- **The Vault (Security)**: Rust daemon (Sarthak) - OS keychain integration, memory encryption
- **The Brain (RAG)**: Python FastAPI (Sailesh) ← **YOUR DOMAIN** 🎯

### What's Currently Implemented ✅
1. **Desktop Chat Interface** - Users can chat with Claude, GPT-4, and Gemini
2. **Encrypted Storage** - Conversations stored in PostgreSQL with AES-256-GCM encryption
3. **Conversation History** - Load/decrypt previous conversations
4. **gRPC Memory Service** (Rust) - Vector embeddings, similarity search with pgvector
5. **Database Setup** - PostgreSQL + pgvector for vector operations
6. **Environment Configuration** - API keys, model selection, context limits

### What's Missing (Your Responsibility) ❌

| Component | Status | Details |
|-----------|--------|---------|
| **main.py** | 🔴 Empty | FastAPI app skeleton not implemented |
| **RAG Orchestration** | 🔴 Not started | Should coordinate between Memory (vector search) and LLM inference |
| **API Endpoints** | 🔴 Not started | Need endpoints for chat, context retrieval, conversation management |
| **Memory Integration** | 🔴 Not started | Should call gRPC gateway to search memories before LLM calls |
| **Embedding Service** | 🔴 Not started | Generate embeddings for queries (or use gateway) |
| **Error Handling** | 🔴 Not started | Graceful degradation, fallback modes |
| **Logging** | 🔴 Not started | Structured logging with tracing |
| **Unit Tests** | 🔴 Not started | Test RAG pipeline, API endpoints |
| **Documentation** | 🔴 Not started | API docs, deployment guide |

### Dependencies ✅
Your `requirements.txt` has:
- `fastapi` - Web framework (only one currently)

### Current Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    IDENTRA ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────┐                          │
│  │  ChatInterface.jsx (React)   │                          │
│  │  ├─ Model selector           │                          │
│  │  ├─ Message input            │                          │
│  │  └─ History sidebar          │                          │
│  └──────────────┬───────────────┘                          │
│                 │                                           │
│                 │ invoke("chat_with_ai")                    │
│                 ▼                                           │
│  ┌──────────────────────────────┐                          │
│  │  commands.rs (Tauri)         │                          │
│  │  ├─ chat_with_ai()           │ ◄─── CALLS LLM APIS    │
│  │  ├─ initialize_session()     │                          │
│  │  └─ query_history()          │                          │
│  └──────────────┬───────────────┘                          │
│                 │                                           │
│       ┌─────────┼─────────┐                                 │
│       │         │         │                                 │
│   Claude      GPT-4    Gemini                               │
│    API        API       API                                 │
│       │         │         │                                 │
│       └─────────┼─────────┘                                 │
│                 │                                           │
│                 ▼                                           │
│  ┌──────────────────────────────┐                          │
│  │  PostgreSQL (encrypted)      │                          │
│  │  ├─ Conversations table       │                          │
│  │  ├─ Memories table           │                          │
│  │  └─ Embeddings (pgvector)    │                          │
│  └──────────────────────────────┘                          │
│                                                             │
│  ┌──────────────────────────────┐                          │
│  │  tunnel-gateway (Rust gRPC)  │ ◄─── NOT INTEGRATED YET│
│  │  ├─ MemoryService            │                          │
│  │  ├─ VaultService             │                          │
│  │  └─ HealthService            │                          │
│  └──────────────────────────────┘                          │
│                                                             │
│  ┌──────────────────────────────┐                          │
│  │  THE BRAIN (YOUR DOMAIN!)    │ 🧠                       │
│  │  ├─ RAG Orchestration        │ ← Build this             │
│  │  ├─ Context Management       │                          │
│  │  ├─ Inference Pipeline       │                          │
│  │  └─ API Endpoints            │                          │
│  └──────────────────────────────┘                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

FLOW WITHOUT BRAIN SERVICE (CURRENT - Direct to LLMs):
User → ChatInterface → Tauri Commands → LLM APIs → PostgreSQL

FLOW WITH BRAIN SERVICE (TARGET - RAG-Enhanced):
User → ChatInterface → Tauri Commands → Brain Service → 
  ├─ Search Memories (gRPC Gateway) → LLM APIs
  ├─ Generate Context
  ├─ Orchestrate Inference
  └─ Store Results → PostgreSQL
```

---

## 🎯 MVP Requirements

### Core MVP Features (To Launch)

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| **Basic FastAPI App** | 🔴 Critical | ❌ Not started | `/health` endpoint minimum |
| **RAG Orchestration** | 🔴 Critical | ❌ Not started | Coordinate memory search + LLM calls |
| **gRPC Gateway Integration** | 🔴 Critical | ❌ Not started | Call tunnel-gateway to search memories |
| **Context Injection** | 🟠 High | ❌ Not started | Add relevant memories to LLM prompts |
| **Environment Config** | 🟠 High | ❌ Not started | Load from .env file |
| **Error Handling** | 🟠 High | ❌ Not started | Graceful fallbacks |
| **Structured Logging** | 🟡 Medium | ❌ Not started | Log all RAG operations |
| **Unit Tests** | 🟡 Medium | ❌ Not started | Test RAG pipeline |
| **API Documentation** | 🟡 Medium | ❌ Not started | Auto-generated from FastAPI |

### Non-MVP (Phase 2)
- Advanced RAG strategies (multi-hop retrieval, reranking)
- Fine-tuning on user memories
- Custom embedding models
- Streaming responses
- Rate limiting & quotas
- Observability dashboards

---

## 📋 Step-by-Step Action Plan

### Phase 1: Setup & Foundation (Days 1-2)

#### Task 1.1: Install `just` Command Runner
- **Priority**: 🔴 Critical
- **Status**: ❌ Not started
- **Time Estimate**: 5 minutes
- **Files to Modify**: None
- **Dependencies**: None
- **Acceptance Criteria**:
  - [ ] `just --version` runs successfully
  - [ ] `just --list` shows all commands
  - [ ] Can run `just dev-brain` without "command not found"

**Implementation Steps**:
```bash
# Option 1: Via Cargo
cargo install just

# Option 2: Via Binary (Linux)
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/casey/just/releases/download/1.34.0/just-1.34.0-x86_64-unknown-linux-gnu.tar.gz | tar xzf - just && sudo mv just /usr/local/bin/

# Verify
just --version
```

**Why**: `just` is the unified task runner. Without it, you can't use `just dev-brain`, `just dev-all`, etc. This blocks everything else.

---

#### Task 1.2: Set Up Python Virtual Environment & Dependencies
- **Priority**: 🔴 Critical
- **Status**: ✅ MOSTLY DONE (You already have `.venv`)
- **Time Estimate**: 2 minutes (just confirm)
- **Files to Modify**: [requirements.txt](apps/brain-service/requirements.txt)
- **Dependencies**: Task 1.1 (have `just` installed)
- **Acceptance Criteria**:
  - [ ] `.venv` exists and is activated
  - [ ] `pip list` shows all required packages
  - [ ] Can import `fastapi`, `pydantic`, `uvicorn`, etc.

**Implementation Steps**:
```bash
cd apps/brain-service

# Activate
source .venv/bin/activate

# Update requirements.txt with all dependencies
cat > requirements.txt << 'EOF'
fastapi==0.128.0
uvicorn[standard]==0.30.0
pydantic==2.12.5
pydantic-settings==2.2.1
python-dotenv==1.0.0
grpcio==1.64.1
grpcio-tools==1.64.1
protobuf==5.27.0
httpx==0.27.0
structlog==24.1.0
EOF

pip install -r requirements.txt
```

**Why**: You need FastAPI, uvicorn, gRPC client libs, and dotenv for configuration. Pydantic for validation. Structlog for logging.

---

#### Task 1.3: Create Basic FastAPI Skeleton
- **Priority**: 🔴 Critical
- **Status**: ❌ Not started
- **Time Estimate**: 15 minutes
- **Files to Modify**: [main.py](apps/brain-service/main.py)
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [ ] `main.py` contains FastAPI app
  - [ ] `/health` endpoint returns `{"status": "ok"}`
  - [ ] Server starts without errors
  - [ ] Can visit `http://localhost:8000/docs` for API docs

**Implementation Steps**:

Update [main.py](apps/brain-service/main.py):
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Identra Brain Service",
    description="RAG Orchestration Engine for Identra Identity Vault",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("🧠 Brain Service starting up...")
    # Initialize gRPC connections, models, etc.

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🧠 Brain Service shutting down...")

@app.get("/health")
async def health_check():
    """Health check endpoint for orchestration"""
    return {"status": "ok", "service": "brain"}

@app.get("/ready")
async def readiness_check():
    """Readiness check - all dependencies initialized"""
    return {"ready": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Why**: This is your foundation. FastAPI auto-generates OpenAPI docs. Health/Ready endpoints are required for orchestration and Kubernetes deployments.

---

### Phase 2: Integration & RAG Core (Days 3-5)

#### Task 2.1: Implement gRPC Client to Tunnel Gateway
- **Priority**: 🔴 Critical
- **Status**: ❌ Not started
- **Time Estimate**: 45 minutes
- **Files to Modify**: 
  - [main.py](apps/brain-service/main.py)
  - Create `clients.py` (new)
- **Dependencies**: Task 1.3
- **Acceptance Criteria**:
  - [ ] Can connect to gRPC gateway on startup
  - [ ] Can call `SearchMemories` RPC successfully
  - [ ] Handles connection failures gracefully
  - [ ] Logs all RPC calls with request/response

**Implementation Steps**:

Create `apps/brain-service/clients.py`:
```python
"""gRPC client for Tunnel Gateway"""
import grpc
import logging
from typing import List, Optional
from identra_proto import memory_pb2, memory_pb2_grpc
import os

logger = logging.getLogger(__name__)

class MemoryServiceClient:
    def __init__(self, gateway_address: Optional[str] = None):
        self.gateway_address = gateway_address or os.getenv("GATEWAY_ADDRESS", "localhost:50051")
        self.channel = None
        self.stub = None
    
    async def connect(self):
        """Connect to gRPC gateway"""
        try:
            # Try secure connection first (production)
            self.channel = grpc.aio.secure_channel(
                self.gateway_address,
                grpc.ssl_channel_credentials()
            )
            self.stub = memory_pb2_grpc.MemoryServiceStub(self.channel)
            logger.info(f"✅ Connected to gRPC gateway at {self.gateway_address} (secure)")
        except Exception as e:
            logger.warning(f"⚠️ Secure connection failed, falling back to insecure: {e}")
            # Fallback to insecure channel for local dev
            try:
                self.channel = grpc.aio.insecure_channel(self.gateway_address)
                self.stub = memory_pb2_grpc.MemoryServiceStub(self.channel)
                logger.info(f"✅ Connected to gRPC gateway at {self.gateway_address} (insecure)")
            except Exception as e2:
                logger.error(f"❌ Failed to connect to gateway: {e2}")
                raise
    
    async def search_memories(
        self, 
        query_embedding: List[float], 
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[dict]:
        """Search memory vault for relevant memories"""
        if not self.stub:
            logger.error("❌ gRPC client not connected")
            return []
        
        try:
            request = memory_pb2.SearchMemoriesRequest(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            response = await self.stub.SearchMemories(request)
            
            logger.info(f"🔍 Memory search returned {len(response.matches)} results")
            return [
                {
                    "id": match.memory.id,
                    "content": match.memory.content,
                    "similarity": match.similarity_score
                }
                for match in response.matches
            ]
        except Exception as e:
            logger.error(f"❌ Memory search failed: {e}")
            return []
    
    async def close(self):
        """Close gRPC channel"""
        if self.channel:
            await self.channel.close()
            logger.info("🔌 Closed gRPC connection")
```

Update [main.py](apps/brain-service/main.py)
        self.gateway_address = gateway_address
        self.channel = None
        self.stub = None
    
    async def connect(self):
        """Connect to gRPC gateway"""
        try:
            self.channel = grpc.aio.secure_channel(
                self.gateway_address,
                grpc.ssl_channel_credentials()
            )
            self.stub = memory_pb2_grpc.MemoryServiceStub(self.channel)
            logger.info(f"✅ Connected to gRPC gateway at {self.gateway_address}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to gateway: {e}")
            # Fallback to insecure channel for local dev
            self.channel = grpc.aio.insecure_channel(self.gateway_address)
            self.stub = memory_pb2_grpc.MemoryServiceStub(self.channel)
    
    async def search_memories(
        self, 
        query_embedding: List[float], 
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[dict]:
        """Search memory vault for relevant memories"""
        try:
            request = memory_pb2.SearchMemoriesRequest(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            response = await self.stub.SearchMemories(request)
            
            logger.info(f"🔍 Memory search returned {len(response.matches)} results")
            return [
                {
                    "id": match.memory.id,
                    "content": match.memory.content,
                    "similarity": match.similarity_score
                }
                for match in response.matches
            ]
        except Exception as e:
            logger.error(f"❌ Memory search failed: {e}")
            return []
    
    async def close(self):
        """Close gRPC channel"""
        if self.channel:
            await self.channel.close()
```

Update [main.py](apps/brain-service/main.py) to use it:
```python
from clients import MemoryServiceClient

memory_client: MemoryServiceClient = None

@app.on_event("startup")
async def startup_event():
    global memory_client
    logger.info("🧠 Brain Service starting up...")
    memory_client = MemoryServiceClient()
    await memory_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    global memory_client
    logger.info("🧠 Brain Service shutting down...")
    if memory_client:
        await memory_client.close()
```

**Why**: The gateway owns memory operations. Your brain service is the **orchestrator** - it coordinates between user input, memory search, and LLM inference. This is the critical linkage.

---

#### Task 2.2: Implement RAG Orchestration Pipeline
- **Priority**: 🔴 Critical
- **Status**: ❌ Not started
- **Time Estimate**: 1 hour
- **Files to Modify**: 
  - [main.py](apps/brain-service/main.py)
  - Create `rag.py` (new)
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - [ ] `RAGPipeline` class implements full orchestration
  - [ ] Can generate embeddings for queries (or use cached embeddings)
  - [ ] Searches memories before each inference
  - [ ] Injects top-K memories into LLM prompt
  - [ ] Handles missing/empty memory results
  - [ ] All operations logged with structured logging

**Implementation Steps**:

Create `apps/brain-service/rag.py`:
```python
"""RAG (Retrieval-Augmented Generation) Orchestration"""
import logging
from typing import List, Optional
from dataclasses import dataclass
from clients import MemoryServiceClient

logger = logging.getLogger(__name__)

@dataclass
class RAGContext:
    """Context for RAG operations"""
    query: str
    memories: List[dict]
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048

class RAGPipeline:
    def __init__(self, memory_client: MemoryServiceClient):
        self.memory_client = memory_client
    
    async def orchestrate(self, query: str, model: str = "claude") -> dict:
        """Full RAG orchestration pipeline"""
        logger.info(f"🚀 Starting RAG for model={model}")
        
        # Get embedding
        query_embedding = self._get_dummy_embedding(query)
        
        # Search memories
        memories = await self.memory_client.search_memories(
            query_embedding=query_embedding,
            limit=5
        )
        logger.info(f"📚 Retrieved {len(memories)} memories")
        
        # Build context
        context = RAGContext(query=query, memories=memories, model=model)
        enhanced_prompt = self._build_prompt(context)
        
        return {
            "query": query,
            "memory_count": len(memories),
            "enhanced_prompt": enhanced_prompt,
            "memories": memories
        }
    
    def _get_dummy_embedding(self, text: str) -> List[float]:
        """TODO: Replace with actual embedding model"""
        return [0.1] * 384
    
    def _build_prompt(self, context: RAGContext) -> str:
        """Build enhanced prompt with memory context"""
        memories_text = ""
        if context.memories:
            memories_text = "### Relevant Context from Memory:\n"
            for i, mem in enumerate(context.memories, 1):
                memories_text += f"{i}. [{mem['similarity']:.2f}] {mem['content']}\n"
        
        return f"""{memories_text}

User: {context.query}

Please use the provided context from the user's memory vault to inform your response."""
```

---

### Phase 3: API Endpoints (Days 5-6)

#### Task 3.1: Add RAG Endpoints
- **Priority**: 🔴 Critical
- **Status**: ❌ Not started
- **Time Estimate**: 1 hour
- **Files to Modify**: [main.py](apps/brain-service/main.py), `rag.py`
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - [ ] `POST /rag/orchestrate` accepts query + model
  - [ ] Returns enhanced prompt + memories
  - [ ] `GET /rag/status` shows pipeline health
  - [ ] All endpoints documented in `/docs`

**API Design**:
```python
from pydantic import BaseModel

class RAGRequest(BaseModel):
    query: str
    model: str = "claude"
    top_k: int = 5
    similarity_threshold: float = 0.7

class RAGResponse(BaseModel):
    query: str
    enhanced_prompt: str
    memories: List[dict]
    memory_count: int

@app.post("/rag/orchestrate", response_model=RAGResponse)
async def orchestrate_rag(request: RAGRequest):
    """Orchestrate RAG pipeline for query"""
    result = await rag_pipeline.orchestrate(
        request.query,
        request.model
    )
    return RAGResponse(**result)

@app.get("/rag/status")
async def rag_status():
    """Check RAG pipeline health"""
    return {
        "status": "ready",
        "memory_service": "connected",
        "embeddings": "loaded"
    }
```

---

#### Task 3.2: Environment Configuration
- **Priority**: 🟠 High
- **Status**: ❌ Not started
- **Time Estimate**: 20 minutes
- **Files to Modify**: Create `.env.example`, `config.py`
- **Dependencies**: Task 1.2
- **Acceptance Criteria**:
  - [ ] `.env.example` documents all variables
  - [ ] `config.py` loads from environment with defaults
  - [ ] Can override with env vars
  - [ ] Secrets never logged

**Implementation**:
```bash
# .env.example
GATEWAY_ADDRESS=localhost:50051
BRAIN_SERVICE_PORT=8000
LOG_LEVEL=INFO
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_MEMORIES=5
SIMILARITY_THRESHOLD=0.7
```

Create `config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gateway_address: str = "localhost:50051"
    brain_service_port: int = 8000
    log_level: str = "INFO"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_memories: int = 5
    similarity_threshold: float = 0.7
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

### Phase 4: Error Handling & Logging (Days 6-7)

#### Task 4.1: Implement Structured Logging
- **Priority**: 🟠 High
- **Status**: ❌ Not started
- **Time Estimate**: 30 minutes
- **Files to Modify**: `main.py`, `rag.py`, `clients.py`
- **Dependencies**: Task 1.3
- **Acceptance Criteria**:
  - [ ] All operations logged with context
  - [ ] Structured JSON logs for production
  - [ ] Log levels: DEBUG, INFO, WARNING, ERROR
  - [ ] No secrets in logs

**Implementation**:
```python
import structlog

# In main.py
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

---

#### Task 4.2: Graceful Error Handling
- **Priority**: 🟠 High
- **Status**: ❌ Not started
- **Time Estimate**: 45 minutes
- **Files to Modify**: `main.py`, `rag.py`
- **Dependencies**: Task 4.1
- **Acceptance Criteria**:
  - [ ] All exceptions caught and logged
  - [ ] Fallback responses for failures
  - [ ] Circuit breaker pattern for gateway
  - [ ] Meaningful error messages

**Implementation**:
```python
from fastapi import HTTPException
from typing import Optional

class RAGError(Exception):
    """RAG pipeline error"""
    pass

@app.post("/rag/orchestrate")
async def orchestrate_rag(request: RAGRequest):
    try:
        result = await rag_pipeline.orchestrate(request.query, request.model)
        return RAGResponse(**result)
    except RAGError as e:
        logger.error("rag_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("unknown_error", error=str(e))
        return RAGResponse(
            query=request.query,
            enhanced_prompt=request.query,  # Fallback to raw query
            memories=[],
            memory_count=0
        )
```

---

### Phase 5: Testing & Documentation (Days 7-8)

#### Task 5.1: Unit Tests for RAG Pipeline
- **Priority**: 🟡 Medium
- **Status**: ❌ Not started
- **Time Estimate**: 1 hour
- **Files to Modify**: Create `test_rag.py`
- **Dependencies**: Task 2.2, Task 4.1
- **Acceptance Criteria**:
  - [ ] Test RAG orchestration
  - [ ] Test memory search
  - [ ] Test prompt building
  - [ ] >80% code coverage
  - [ ] All tests pass

**Implementation**:
```python
# test_rag.py
import pytest
from rag import RAGPipeline, RAGContext
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_orchestrate_with_memories():
    """Test RAG orchestration returns enhanced prompt"""
    mock_client = AsyncMock()
    mock_client.search_memories.return_value = [
        {"id": "1", "content": "Memory 1", "similarity": 0.95}
    ]
    
    pipeline = RAGPipeline(mock_client)
    result = await pipeline.orchestrate("test query")
    
    assert result["memory_count"] == 1
    assert "Memory 1" in result["enhanced_prompt"]
    assert mock_client.search_memories.called

@pytest.mark.asyncio
async def test_orchestrate_no_memories():
    """Test RAG with no memory matches"""
    mock_client = AsyncMock()
    mock_client.search_memories.return_value = []
    
    pipeline = RAGPipeline(mock_client)
    result = await pipeline.orchestrate("test query")
    
    assert result["memory_count"] == 0
    assert result["enhanced_prompt"] != ""
```

---

#### Task 5.2: Integration Tests
- **Priority**: 🟡 Medium
- **Status**: ❌ Not started
- **Time Estimate**: 1.5 hours
- **Files to Modify**: Create `test_integration.py`
- **Dependencies**: Task 3.1, Task 4.2
- **Acceptance Criteria**:
  - [ ] Test API endpoints
  - [ ] Test with real gRPC client
  - [ ] Test error scenarios
  - [ ] All tests pass

---

#### Task 5.3: API Documentation
- **Priority**: 🟡 Medium
- **Status**: ❌ Not started
- **Time Estimate**: 30 minutes
- **Files to Modify**: Create `BRAIN_SERVICE.md`
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - [ ] Document all endpoints
  - [ ] Provide curl examples
  - [ ] Document error codes
  - [ ] Deployment instructions

---

### Phase 6: Production Readiness (Days 8-9)

#### Task 6.1: Docker Configuration
- **Priority**: 🟡 Medium
- **Status**: ❌ Not started
- **Time Estimate**: 30 minutes
- **Files to Modify**: Create `Dockerfile`
- **Dependencies**: Task 3.2

**Implementation**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### Task 6.2: Health Checks & Observability
- **Priority**: 🟡 Medium
- **Status**: ❌ Not started
- **Time Estimate**: 45 minutes
- **Files to Modify**: `main.py`
- **Dependencies**: Task 4.1

**Implementation**:
```python
@app.get("/health")
async def health():
    """Liveness probe"""
    return {"status": "alive"}

@app.get("/ready")
async def readiness():
    """Readiness probe - all dependencies ready"""
    gateway_ok = memory_client.channel is not None
    return {
        "ready": gateway_ok,
        "gateway": "connected" if gateway_ok else "disconnected"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "requests_total": 0,  # TODO: Track with middleware
        "latency_ms": 0,
        "errors_total": 0
    }
```

---

## 📈 Progress Tracking

Track your completion with this checklist:

### Week 1: Foundation & Integration
- [ ] Task 1.1: Install `just`
- [ ] Task 1.2: Setup venv & dependencies
- [ ] Task 1.3: FastAPI skeleton
- [ ] Task 2.1: gRPC client
- [ ] Task 2.2: RAG orchestration
- [ ] Task 3.1: API endpoints

**Target**: Have working `/rag/orchestrate` endpoint by end of Week 1

### Week 2: Production Hardening
- [ ] Task 3.2: Environment config
- [ ] Task 4.1: Structured logging
- [ ] Task 4.2: Error handling
- [ ] Task 5.1: Unit tests
- [ ] Task 5.2: Integration tests
- [ ] Task 5.3: Documentation
- [ ] Task 6.1: Docker
- [ ] Task 6.2: Health checks

**Target**: Brain service ready for staging deployment

---

## 🔧 Development Workflow

### Daily Standup Checklist
Each day before coding:
```bash
# 1. Sync with main
git checkout main && git pull origin main

# 2. Create feature branch
git checkout -b feature/brain-{task-number}

# 3. Start development
source .venv/bin/activate
just dev-brain  # or: python main.py

# 4. After changes, commit
git add .
git commit -m "feat(brain): Task X.Y description"
git pull origin main --rebase
git push origin feature/brain-{task-number}

# 5. Create PR for review (Manish & Sarthak)
```

### Testing Locally
```bash
cd apps/brain-service

# Unit tests
pytest test_rag.py -v

# Integration tests
pytest test_integration.py -v

# Coverage
pytest --cov=. --cov-report=html

# Start service manually
source .venv/bin/activate
python main.py

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

curl -X POST http://localhost:8000/rag/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "What do I remember about AI?", "model": "claude"}'
```

---

## 📚 Key Resources

| Resource | Purpose | Link |
|----------|---------|------|
| **Identra README** | Architecture overview | [README.md](README.md) |
| **Copilot Instructions** | Team workflow & patterns | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| **Chat Setup** | Current chat implementation | [CHAT_SETUP.md](CHAT_SETUP.md) |
| **Implementation Summary** | What's been built | [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) |
| **FastAPI Docs** | REST framework guide | https://fastapi.tiangolo.com/ |
| **gRPC Python** | gRPC client guide | https://grpc.io/docs/languages/python/ |

---

## 🎯 Success Metrics

Your MVP is complete when:

✅ **Functional**
- Brain service starts without errors
- `/rag/orchestrate` endpoint works end-to-end
- Memories are injected into prompts
- Handles 100+ qps without crashing

✅ **Integrated**
- Connected to tunnel-gateway gRPC
- Can search PostgreSQL via gateway
- Tauri commands can call brain service (future integration)

✅ **Production-Ready**
- All errors logged and handled gracefully
- Unit test coverage >80%
- Docker image builds and runs
- Health checks pass
- API docs complete

✅ **Documented**
- README with setup instructions
- API documentation
- Architecture diagrams
- Deployment guide

---

## ⚠️ Common Pitfalls (Avoid These!)

1. **Not testing locally first** - Use `curl` to test endpoints before integrating
2. **Blocking on perfect embeddings** - Start with dummy embeddings, improve later
3. **Ignoring error handling** - Network failures WILL happen, plan for them
4. **Skipping logging** - You'll need logs to debug production issues
5. **Tight coupling to LLM APIs** - Keep interface abstracted, easy to swap models
6. **No graceful degradation** - If gateway is down, service should still respond

---

## 💬 Communication

- **Team Slack**: #identra-development
- **Daily Standup**: 9:30 AM PT
- **Code Review**: Manish (Rust/Architecture), Sarthak (gRPC/Gateway)
- **Questions**: Ask in Slack before spending >30 min stuck

---

## 🚀 Next Steps (After MVP)

1. **Phase 2: Advanced RAG**
   - Multi-hop retrieval (memories → relevant memories)
   - Reranking with cross-encoders
   - Hybrid search (semantic + keyword)

2. **Phase 3: Streaming**
   - Server-sent events for streaming responses
   - Real-time memory injection

3. **Phase 4: Observability**
   - Prometheus metrics
   - Grafana dashboards
   - Distributed tracing (Jaeger)

4. **Phase 5: Production Hardening**
   - Load testing
   - Circuit breakers
   - Rate limiting
   - Caching layer

---

**Good luck, Sailesh!** 🚀 You've got this. Start with Task 1.1 and work your way through. Remember to commit early and often, and don't hesitate to ask for code reviews.
class RAGPipeline:
    def __init__(self, memory_client: MemoryServiceClient):
        self.memory_client = memory_client
    
    async def orchestrate(self, query: str, model: str = "claude") -> dict:
        """
        Orchestrate full RAG pipeline:
        1. Embed query (or use raw query for memory search)
        2. Search memories
        3. Build context
        4. Call LLM (via Tauri, eventually)
        5. Store result
        """
        logger.info(f"🚀 Starting RAG orchestration for model={model}")
        
        # Step 1: Get query embedding
        # TODO: Use actual embedding model (AllMiniLM or similar)
        query_embedding = self._get_dummy_embedding(query)
        
        # Step 2: Search memories
        memories = await self.memory_client.search_memories(
            query_embedding=query_embedding,
            limit=5,
            similarity_threshold=0.7
        )
        logger.info(f"📚 Retrieved {len(memories)} relevant memories")
        
        # Step 3: Build RAG context
        context = RAGContext(
            query=query,
            memories=memories,
            model=model
        )
        
        # Step 4: Build enhanced prompt
        enhanced_prompt = self._build_prompt(context)
        
        logger.info("✅ RAG orchestration complete. Ready for inference.")
        return {
            "query": query,
            "memory_count": len(memories),
            "enhanced_prompt": enhanced_prompt,
            "memories": memories
        }
    
    def _get_dummy_embedding(self, text: str) -> List[float]:
        """
        TODO: Replace with actual embedding model
        For now, return dummy embedding for testing
        """
        # Placeholder: would use AllMiniLM-L6-v2 in production
        return [0.1] * 384  # Dummy 384-dim embedding
    
    def _build_prompt(self, context: RAGContext) -> str:
        """Build enhanced prompt with memory context"""
        memories_text = ""
        if context.memories:
            memories_text = "### Relevant Context from Memory:\n"
            for i, mem in enumerate(context.memories, 1):
                memories_text += f"{i}. [{mem['similarity']:.2f}] {mem['content']}\n"
        
        prompt = f"""You are Identra, a helpful AI assistant with access to the user's personal memory vault.

{memories_text}

User: {context.query}