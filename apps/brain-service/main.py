import os
import time
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# ─── Load settings ───────────────────────────────────────────────────────
from src.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("brain_service")

# ─── Read API keys from settings ─────────────────────────────────────────────
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
OPENAI_API_KEY    = settings.OPENAI_API_KEY
GEMINI_API_KEY    = settings.GEMINI_API_KEY
ANTHROPIC_MODEL   = settings.ANTHROPIC_MODEL
OPENAI_MODEL      = settings.OPENAI_MODEL
GEMINI_MODEL      = settings.GEMINI_MODEL
HF_API_KEY        = settings.HF_API_KEY
HF_MODEL          = settings.HF_MODEL

# ─── Import AI clients ───────────────────────────────────────────────────────
from src.ai.clients.claude_client  import ClaudeClient
from src.ai.clients.openai_client  import OpenAIClient
from src.ai.clients.gemini_client       import GeminiClient
from src.ai.clients.huggingface_client  import HuggingFaceClient
from src.ai.clients.base_client    import AIRequest, AIMessage, ModelProvider
from src.memory.conversation_store import ConversationStore
from src.rag.rag_pipeline import RAGPipeline
from src.rag.embedding_service import EmbeddingService
from src.grpc.server import GRPCServer

# ─── Global singletons (initialised in lifespan) ─────────────────────────────
claude_client:  Optional[ClaudeClient]  = None
openai_client:  Optional[OpenAIClient]  = None
gemini_client:  Optional[GeminiClient]  = None
hf_client:      Optional[HuggingFaceClient] = None
conversation_store: Optional[ConversationStore] = None
embedding_service: Optional[EmbeddingService] = None
rag_pipeline: Optional[RAGPipeline] = None
grpc_server: Optional[GRPCServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global claude_client, openai_client, gemini_client, hf_client, conversation_store, rag_pipeline, grpc_server, embedding_service

    # ── AI clients ────────────────────────────────────────────────────────
    if ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("your_"):
        try:
            claude_client = ClaudeClient(api_key=ANTHROPIC_API_KEY)
            logger.info("✅ Claude client ready")
        except Exception as e:
            logger.warning(f"⚠️  Claude init failed: {e}")

    if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("your_"):
        try:
            openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
            logger.info("✅ OpenAI client ready")
        except Exception as e:
            logger.warning(f"⚠️  OpenAI init failed: {e}")

    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
        try:
            gemini_client = GeminiClient(api_key=GEMINI_API_KEY)
            logger.info("✅ Gemini client ready")
        except Exception as e:
            logger.warning(f"⚠️  Gemini init failed: {e}")

    if HF_API_KEY and not HF_API_KEY.startswith("your_"):
        try:
            hf_client = HuggingFaceClient(api_key=HF_API_KEY)
            logger.info("✅ HuggingFace client ready")
        except Exception as e:
            logger.warning(f"⚠️  HuggingFace init failed: {e}")

    # ── Conversation store ────────────────────────────────────────────────
    try:
        embedding_service = EmbeddingService()
        conversation_store = ConversationStore(db_path="conversations.db", embedding_service=embedding_service)
        await conversation_store.initialize()
        logger.info("✅ Conversation store ready")
    except Exception as e:
        logger.warning(f"⚠️  Conversation store init failed: {e}")

    providers = []
    if claude_client:  providers.append("Claude")
    if openai_client:  providers.append("OpenAI")
    if gemini_client:  providers.append("Gemini")
    if hf_client:      providers.append("HuggingFace")
    try:
        rag_pipeline = RAGPipeline(db_path="conversations.db", embedding_service=embedding_service)
        logger.info("✅ RAG Pipeline ready")
    except Exception as e:
        logger.warning(f"⚠️  RAG Pipeline init failed: {e}")

    try:
        if conversation_store:
            grpc_server = GRPCServer(conversation_store, embedding_service=embedding_service)
            grpc_server.start()
            logger.info("✅ gRPC server ready on port 50051")
    except Exception as e:
        logger.warning(f"⚠️  gRPC server failed: {e}")

    logger.info(f"🧠 Brain Service started — active providers: {providers or ['none (demo mode)']}")

    yield  # app runs here

    if grpc_server:
        grpc_server.stop()
    logger.info("🛑 Brain Service shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Identra Brain Service",
    version="2.0",
    description="Multi-model AI + memory for Identra",
    lifespan=lifespan,
)


# ─── Pydantic models ─────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    user_id:    str = "default_user"
    message:    str
    provider:   Optional[str] = None   # "claude" | "openai" | "gemini" | None (auto)
    context:    Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response:        str
    model_used:      str
    provider:        str
    session_id:      str
    processing_time: float

class MemoryRequest(BaseModel):
    content:    str
    session_id: str
    user_id:    str = "default_user"
    role:       str = "user"

class MemorySearchRequest(BaseModel):
    query:   str
    user_id: str = "default_user"
    limit:   int = 5

class HealthResponse(BaseModel):
    status:    str
    providers: Dict[str, bool]
    version:   str


# ─── Helper: pick best available client ──────────────────────────────────────
def _pick_client(preferred: Optional[str]):
    """Return (client, provider_name, model_name) for the best available provider."""
    
    order = []

    if preferred == "claude"  and claude_client:  order = [(claude_client,  "claude",  ANTHROPIC_MODEL)]
    elif preferred == "openai" and openai_client: order = [(openai_client, "openai",  OPENAI_MODEL)]
    elif preferred == "gemini" and gemini_client: order = [(gemini_client, "gemini",  GEMINI_MODEL)]
    else:
        # Auto-select: HuggingFace → Gemini → OpenAI → Claude
        if hf_client:      order.append((hf_client,      "huggingface", HF_MODEL))
        if gemini_client:  order.append((gemini_client, "gemini",  GEMINI_MODEL))
        if openai_client:  order.append((openai_client, "openai",  OPENAI_MODEL))
        if claude_client:  order.append((claude_client,  "claude",  ANTHROPIC_MODEL))

    if not order:
        return None, None, None

    return order[0]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="Brain Service is alive and thinking! 🧠",
        providers={
            "claude":  claude_client  is not None,
            "openai":  openai_client  is not None,
            "gemini":  gemini_client  is not None,
            "huggingface": hf_client is not None,
            "memory":  conversation_store is not None,
        },
        version="2.0",
    )


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    start_time = time.time()

    client, provider_name, model_name = _pick_client(request.provider)

    # ── Demo / mock mode when no provider is available ────────────────────
    if client is None:
        return ChatResponse(
            response=(
                f"[DEMO MODE] No AI provider configured. "
                f"Your message: '{request.message}'"
            ),
            model_used="demo",
            provider="demo",
            session_id=request.session_id,
            processing_time=round(time.time() - start_time, 3),
        )

    # ── Build message history from memory ────────────────────────────────
    history: List[AIMessage] = []
    if conversation_store:
        try:
            past = await conversation_store.search_conversations(
                user_id=request.user_id,
                query=request.message,
                limit=5,
            )
            for conv in reversed(past):
                history.append(AIMessage(role=conv.role, content=conv.message))
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")

    # RAG: Retrieve relevant memories and augment prompt
    rag_result = {"augmented_prompt": request.message, "memories_used": 0}
    if rag_pipeline:
        try:
            rag_result = rag_pipeline.process(
                query=request.message,
                user_id=request.user_id,
                top_k=5
            )
            logger.info(f"🧠 RAG used {rag_result['memories_used']} memories")
        except Exception as e:
            logger.warning(f"RAG failed: {e}")

    # Add Identra system prompt
    system_prompt = AIMessage(
        role="system",
        content=(
            "You are Identra, an intelligent AI assistant built to help developers "
            "and teams work smarter. You are helpful, concise, and friendly. "
            "You were created by the Identra team. Never say you are Qwen, Claude, "
            "GPT, or any other AI. You are always Identra."
        )
    )
    history.insert(0, system_prompt)

    # Add current message
    history.append(AIMessage(role="user", content=rag_result["augmented_prompt"]))

    ai_request = AIRequest(
        messages=history,
        model_name=model_name,
        temperature=0.7,
        max_tokens=1024,
        user_id=request.user_id,
        conversation_id=request.session_id,
    )

    try:
        ai_response = await client.generate_response(ai_request)

        # ── Store both turns in memory ────────────────────────────────
        if conversation_store:
            try:
                await conversation_store.store_message(
                    user_id=request.user_id,
                    message=request.message,
                    role="user",
                    conversation_id=request.session_id,
                )
                await conversation_store.store_message(
                    user_id=request.user_id,
                    message=ai_response.content,
                    role="assistant",
                    conversation_id=request.session_id,
                )
            except Exception as e:
                logger.warning(f"Memory store failed: {e}")

        return ChatResponse(
            response=ai_response.content,
            model_used=ai_response.model_used,
            provider=provider_name,
            session_id=request.session_id,
            processing_time=round(time.time() - start_time, 3),
        )

    except Exception as e:
        logger.error(f"Chat error ({provider_name}): {e}")
        raise HTTPException(status_code=500, detail=f"{provider_name} error: {str(e)}")


@app.post("/api/v1/memory/store")
async def store_memory(request: MemoryRequest):
    if not conversation_store:
        return {"status": "skipped", "reason": "Memory store not available"}
    try:
        await conversation_store.store_message(
            user_id=request.user_id,
            message=request.content,
            role=request.role,
            conversation_id=request.session_id,
        )
        return {"status": "success", "saved_content": request.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory store error: {str(e)}")


@app.post("/api/v1/memory/search")
async def search_memory(request: MemorySearchRequest):
    if not conversation_store:
        return {"results": [], "reason": "Memory store not available"}
    try:
        results = await conversation_store.search_conversations(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit,
        )
        return {
            "results": [
                {
                    "message":           r.message,
                    "role":              r.role,
                    "timestamp":         r.timestamp.isoformat(),
                    "similarity_score":  round(r.similarity_score, 4),
                    "conversation_id":   r.conversation_id,
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory search error: {str(e)}")


@app.get("/api/v1/models")
async def list_models():
    """List all available AI models."""
    available: Dict[str, Any] = {}
    if claude_client:
        available["claude"] = {"models": claude_client.get_available_models(), "default": ANTHROPIC_MODEL}
    if openai_client:
        available["openai"] = {"models": openai_client.get_available_models(), "default": OPENAI_MODEL}
    if gemini_client:
        available["gemini"] = {"models": gemini_client.get_available_models(), "default": GEMINI_MODEL}
    if hf_client:
        available["huggingface"] = {"models": hf_client.get_available_models(), "default": HF_MODEL}
    return {"available_providers": available}


@app.get("/api/v1/usage")
async def usage_stats():
    """Return token usage and cost across all providers."""
    stats: Dict[str, Any] = {}
    if claude_client:  stats["claude"]  = claude_client.get_usage_summary()
    if openai_client:  stats["openai"]  = openai_client.get_usage_summary()
    if gemini_client:  stats["gemini"]  = gemini_client.get_usage_summary()
    if hf_client:      stats["huggingface"] = hf_client.get_usage_summary()
    return stats