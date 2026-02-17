"""
Identra Brain-Service - Universal AI Memory & RAG Orchestration

The AI orchestration layer for the Identra confidential memory vault ecosystem.
Provides universal conversation handling with custom fine-tuned summarization,
multi-model AI routing, and RAG-powered context management.

Team Ownership: Sailesh (AI/RAG/ML components)
Integration: Sarthak (gRPC), Manish & OmmPrakash (Desktop)
"""

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- IMPORTS FOR SUMMARIZER SERVICE ---
# Import from the actual filename: Summarizer_service.py (capital S)
try:
    from src.ai.summarizer_service import (
        SummarizerService, 
        SummarizationRequest, 
        SummarizationResponse
    )
    SUMMARIZER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: SummarizerService not found ({e}). Running in Safe Mode.")
    SUMMARIZER_AVAILABLE = False
    
    # Fallback dummy classes to prevent crashes
    class SummarizationRequest(BaseModel):
        text: str
        options: dict = {}
    class SummarizationResponse(BaseModel):
        summary: str
        metrics: dict
        warnings: list = []

# --- IMPORTS FOR UNIVERSAL BRAIN ---
try:
    from src.engine.universal_brain import UniversalBrainService
    BRAIN_AVAILABLE = True
    print("✅ UniversalBrainService imported successfully")
except ImportError as e:
    print(f"⚠️ Warning: UniversalBrainService not found ({e}). '/process' will use mocks.")
    BRAIN_AVAILABLE = False
except Exception as e:
    print(f"⚠️ Error importing UniversalBrainService: {e}")
    BRAIN_AVAILABLE = False

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
    components: dict[str, str]

class ProcessConversationRequest(BaseModel):
    user_message: str
    user_id: str
    conversation_id: str | None = None
    target_model: str = "claude"
    context_hints: list[str] = []

class ProcessConversationResponse(BaseModel):
    ai_response: str
    conversation_type: str
    context_theme: str
    memory_effectiveness: str
    context_used: list[dict] = []

class BuildContextRequest(BaseModel):
    conversation_blocks: list[str]
    conversation_type: str
    target_llm: str = "claude"
    user_id: str

class BuildContextResponse(BaseModel):
    context_pack: dict
    llm_injection_format: str
    compression_ratio: float

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

# Initialize Summarizer
summarizer_engine = SummarizerService() if SUMMARIZER_AVAILABLE else None

# Initialize Universal Brain
try:
    brain_engine = UniversalBrainService() if BRAIN_AVAILABLE else None
    if brain_engine:
        print("🧠 Universal Brain: Online")
except Exception as e:
    print(f"⚠️ Failed to initialize Universal Brain: {e}")
    brain_engine = None
    BRAIN_AVAILABLE = False

# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    """
    print("\n🚀 Identra Brain-Service Starting...")
    print("📁 Working Directory:", os.getcwd())
    
    # Check Components
    if summarizer_engine:
        print("✅ Summarizer Engine: Online (Llama 3.1 / Mistral)")
    else:
        print("❌ Summarizer Engine: Offline")

    if brain_engine:
        print("✅ Universal Brain: Online (Orchestrator Ready)")
    else:
        print("❌ Universal Brain: Offline (Using Mock Responses)")
    
    print("🌐 Server will be available at: http://localhost:8001")
    print("📋 Health check: http://localhost:8001/health")
    
    yield  # Application runs here
    
    print("🔄 Shutting down Brain-Service...")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Identra Brain-Service",
    description="Universal AI Memory & RAG Orchestration",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:1420"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        message="Identra Brain-Service is running",
        version="0.1.0",
        components={
            "summarization_model": "online" if summarizer_engine else "offline",
            "universal_brain": "online" if brain_engine else "offline",
            "memory_integration": "connecting"
        }
    )

@app.post("/summarize", response_model=SummarizationResponse)
async def summarize_content(request: SummarizationRequest) -> SummarizationResponse:
    """Universal Summarization Endpoint."""
    if not summarizer_engine:
        raise HTTPException(status_code=503, detail="Summarizer service is not available")
    
    try:
        response = await summarizer_engine.summarize(request)
        return response
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Summarization Error: {e}")
        raise HTTPException(status_code=500, detail="Internal summarization error")

@app.post("/process", response_model=ProcessConversationResponse)
async def process_conversation(request: ProcessConversationRequest) -> ProcessConversationResponse:
    """
    RAG-powered conversation context processing.
    
    YOUR ACTUAL RESPONSIBILITIES:
    1. Retrieve relevant conversation history (RAG)
    2. Build context for ANY model (user/tunnel-gateway chooses model)
    3. Manage conversation memory and summarization
    4. Return enriched context + conversation classification
    """
    try:
        if brain_engine:
            # Call the corrected RAG-focused method
            result = await brain_engine.process_rag_context(
                user_message=request.user_message,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                context_hints=request.context_hints
            )
            
            return ProcessConversationResponse(
                ai_response=result["ai_response"],  # ✅ FIXED: Changed from context_summary
                conversation_type=result["conversation_type"], 
                context_theme=result["context_theme"],
                memory_effectiveness=result["memory_effectiveness"],
                context_used=result["context_used"]  # Actual retrieved conversations
            )
        else:
            # --- FALLBACK MOCK LOGIC ---
            return ProcessConversationResponse(
                ai_response=f"Mock Response: {request.user_message}",
                conversation_type="mock",
                context_theme="none",
                memory_effectiveness="zero",
                context_used=[]
            )

    except Exception as e:
        print(f"RAG Processing Error: {e}")
        raise HTTPException(status_code=500, detail=f"RAG Error: {str(e)}")

@app.post("/build-context", response_model=BuildContextResponse)
async def build_context(request: BuildContextRequest) -> BuildContextResponse:
    """
    Build LLM-optimized context pack from conversation blocks.
    """
    try:
        if brain_engine:
            # --- REAL BRAIN LOGIC ---
            result = await brain_engine.build_context_pack(
                conversation_blocks=request.conversation_blocks,
                conversation_type=request.conversation_type,
                target_llm=request.target_llm,
                user_id=request.user_id
            )
            
            return BuildContextResponse(
                context_pack=result["context_pack"],
                llm_injection_format=result["llm_injection_format"],
                compression_ratio=result["compression_ratio"]
            )
        else:
            # --- FALLBACK MOCK LOGIC ---
            return BuildContextResponse(
                context_pack={
                    "context_type": "conversation_memory",
                    "conversation_metadata": {
                        "type": request.conversation_type,
                        "participants": [request.user_id],
                        "created_at": "2026-02-04T10:30:00Z"
                    },
                    "memory_content": {
                        "summary": "Context construction logic coming next step",
                        "key_points": ["point1", "point2"],
                    }
                },
                llm_injection_format=f"Optimized for {request.target_llm}",
                compression_ratio=0.3
            )
    except Exception as e:
        print(f"Context Building Error: {e}")
        raise HTTPException(status_code=500, detail="Internal context building error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 