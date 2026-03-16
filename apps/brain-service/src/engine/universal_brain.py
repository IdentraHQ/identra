import logging
import asyncio
import psutil  # For memory detection
import subprocess
from typing import Dict, List
from src.memory.conversation_store import ConversationStore

# --- CONFIGURATION ---
MOCK_MODE = True  # Keep as True for now

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("universal_brain")

# Only import heavy AI libraries if we are NOT in Mock Mode
if not MOCK_MODE:
    try:
        import ollama
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False
        logger.warning("Ollama not available - real mode will fail")
else:
    OLLAMA_AVAILABLE = False

class UniversalBrainService:
    def __init__(self):
        self.conversation_store = ConversationStore()
        
        # Smart model selection based on available memory
        self.LOCAL_MODEL = self._select_optimal_model()
        self._initialized = False
        
        if MOCK_MODE:
            logger.info("🧠 Universal Brain Online - MOCK MODE ACTIVE (RAM Saved 💾)")
        else:
            logger.info(f"🧠 Universal Brain Online - REAL AI MODE ({self.LOCAL_MODEL})")
            if not OLLAMA_AVAILABLE:
                logger.error("❌ Ollama not available for real mode!")

    def _select_optimal_model(self) -> str:
        """
        Automatically select the best model based on available system memory
        """
        try:
            # Get available memory in GB
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
            
            logger.info(f"💾 Available system memory: {available_memory_gb:.1f} GB")
            
            # Model selection based on memory
            if available_memory_gb >= 8.0:
                return "llama3.1:8b"  # High quality, needs 4.8GB
            elif available_memory_gb >= 4.0:
                return "llama3.2:3b"  # Good balance, needs 2.0GB  
            elif available_memory_gb >= 2.5:
                return "llama3.2:1b"  # Memory efficient, needs 1.3GB
            else:
                return "phi3:mini"    # Ultra-light, works on 2GB systems
                
        except Exception as e:
            logger.warning(f"Memory detection failed: {e}")
            return "llama3.2:1b"  # Safe default

    async def initialize(self):
        """Initialize database and detect available AI model"""
        if not self._initialized:
            await self.conversation_store.initialize()
            
            # Auto-detect available model in real mode
            if not MOCK_MODE and OLLAMA_AVAILABLE:
                self.LOCAL_MODEL = await self._find_available_model()
                if self.LOCAL_MODEL:
                    logger.info(f"✅ AI Model Ready: {self.LOCAL_MODEL}")
                else:
                    logger.error("❌ No AI models found! Install with: ollama pull mistral:7b")
            
            self._initialized = True

    async def _find_available_model(self) -> Optional[str]:
        """Auto-detect first available Ollama model"""
        try:
            import ollama
            
            # Check if Ollama server is running
            try:
                models_response = ollama.list()
            except Exception as e:
                logger.error(f"❌ Ollama server not running: {e}")
                logger.info("💡 Start Ollama with: ollama serve")
                return None
            
            available = [m['name'] for m in models_response.get('models', [])]
            logger.info(f"📋 Available models: {available}")
            
            # Find first match from priority list
            for preferred in self.MODEL_PRIORITY:
                for available_model in available:
                    if preferred in available_model:
                        return available_model
            
            # Use any available model as fallback
            if available:
                logger.warning(f"⚠️ Using fallback: {available[0]}")
                return available[0]
            
            logger.error("❌ No models installed!")
            logger.info("💡 Install a model: ollama pull mistral:7b")
            return None
            
        except Exception as e:
            logger.error(f"Model detection error: {e}")
            return None

    async def process_conversation(
        self, 
        user_message: str, 
        user_id: str, 
        conversation_id: str = None, 
        target_model: str = "claude", 
        context_hints: List[str] = None
    ) -> Dict:
        """Wrapper for main.py compatibility"""
        return await self.process_rag_context(
            user_message=user_message,
            user_id=user_id, 
            conversation_id=conversation_id
        )

    async def process_rag_context(
        self, 
        user_message: str, 
        user_id: str, 
        conversation_id: str = None, 
        **kwargs
    ) -> Dict:
        """Main RAG processing pipeline"""
        if not self._initialized:
            await self.initialize()
        
        conversation_id = conversation_id or f"chat_{user_id}"

        try:
            # 1. Store user message
            await self.conversation_store.store_message(
                user_id=user_id,
                message=user_message, 
                role="user",
                conversation_id=conversation_id,
                conversation_type="rag_chat"
            )
            
            # 2. Retrieve relevant memories
            memories = await self.conversation_store.search_conversations(
                user_id=user_id, 
                query=user_message[:50], 
                limit=3
            )
            
            # 3. Generate response
            if MOCK_MODE:
                response_text = self._generate_mock_response(user_message, memories)
            else:
                context_text = "\n".join([f"- {m.message}" for m in memories]) if memories else "No context"
                response_text = await self._generate_real_response(user_message, context_text)

            # 4. Store AI response
            await self.conversation_store.store_message(
                user_id=user_id,
                message=response_text,
                role="assistant", 
                conversation_id=conversation_id,
                conversation_type="rag_chat"
            )

            # 5. Return formatted response
            return {
                "ai_response": response_text,
                "conversation_type": "rag_chat", 
                "context_theme": "memory_enhanced",
                "memory_effectiveness": f"Retrieved {len(memories)} memories",
                "context_used": [
                    {
                        "message": m.message[:100] + "..." if len(m.message) > 100 else m.message,
                        "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') else "recent",
                        "conversation_type": m.conversation_type or "chat"
                    }
                    for m in memories
                ]
            }

        except Exception as e:
            logger.error(f"❌ Processing error: {e}", exc_info=True)
            return {
                "ai_response": f"System error: {str(e)}",
                "conversation_type": "error",
                "context_theme": "system_error", 
                "memory_effectiveness": "failed",
                "context_used": []
            }

    def _generate_mock_response(self, user_message: str, memories: List) -> str:
        """Mock responses for testing without AI"""
        if not memories:
            return (
                f"🤖 [MOCK] Processing: '{user_message[:60]}...'\n\n"
                f"✅ RAG System: Online\n"
                f"✅ Database: Connected\n"
                f"❌ Found: 0 memories\n\n"
                f"(Enable REAL MODE to get AI-powered responses)"
            )
        
        top_memory = memories[0].message
        return (
            f"🤖 [MOCK] RAG Success!\n\n"
            f"Retrieved {len(memories)} memories:\n"
            f"• '{top_memory[:80]}...'\n\n"
            f"(Real AI would use this context to answer: '{user_message}')"
        )

    async def _generate_real_response(self, message: str, similar_conversations: List) -> str:
        """
        Enhanced real AI generation with better prompt engineering and error handling
        """
        if not OLLAMA_AVAILABLE:
            return "❌ Real mode requested but Ollama is not installed. Run: curl -fsSL https://ollama.ai/install.sh | sh"
        
        try:
            # Check if model is available, provide helpful message if not
            available_models = await self._get_available_models()
            if self.LOCAL_MODEL not in available_models:
                return f"❌ Model {self.LOCAL_MODEL} not found. Run: ollama pull {self.LOCAL_MODEL}"
            
            logger.info(f"🤔 Generating response with {self.LOCAL_MODEL}...")
            
            # Build context from similar conversations
            context = self._format_context(similar_conversations)
            
            # Enhanced prompt engineering
            system_prompt = self._build_system_prompt()
            user_prompt = self._format_user_prompt(message, context)
            
            response = ollama.generate(
                model=self.LOCAL_MODEL,
                prompt=user_prompt,
                system=system_prompt,
                options=self._get_model_options()
            )
            
            logger.info("✅ Real AI response generated successfully")
            return self._post_process_response(response['response'])
            
        except Exception as e:
            return self._handle_ai_error(e)

    def _build_system_prompt(self) -> str:
        """Build optimized system prompt based on model capabilities"""
        base_prompt = (
            "You are Identra, a private AI assistant with conversation memory. "
            "Be helpful, concise, and natural in your responses. "
        )
        
        # Adjust complexity based on model size
        if "8b" in self.LOCAL_MODEL:
            return base_prompt + "Use the conversation context to provide detailed, insightful responses."
        elif "3b" in self.LOCAL_MODEL:
            return base_prompt + "Use the conversation context to provide relevant, contextual responses."
        else:  # 1b or smaller models
            return base_prompt + "Keep responses clear and direct."

    def _format_context(self, similar_conversations: List) -> str:
        """Format retrieved conversations into context"""
        if not similar_conversations:
            return "No past conversations found."
        
        context_parts = []
        for i, conv in enumerate(similar_conversations):
            snippet = conv.message[:150] + "..." if len(conv.message) > 150 else conv.message
            context_parts.append(f"{i+1}. {conv.role}: {snippet}")
        
        return "\n".join(context_parts)

    def _format_user_prompt(self, message: str, context: str) -> str:
        """Format context and message for optimal model performance"""
        if context == "No past conversations found.":
            return f"User: {message}\n\nAssistant:"
        
        return f"""Previous conversations:
{context}

Current message: {message}

Response:"""

    def _get_model_options(self) -> Dict:
        """Get optimal parameters for the selected model"""
        base_options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
        
        # Adjust parameters based on model size
        if "8b" in self.LOCAL_MODEL:
            base_options.update({
                "num_ctx": 8192,
                "num_predict": 512
            })
        elif "3b" in self.LOCAL_MODEL:
            base_options.update({
                "num_ctx": 4096,
                "num_predict": 256
            })
        else:  # 1b or smaller
            base_options.update({
                "num_ctx": 2048,
                "num_predict": 150
            })
        
        return base_options

    def _post_process_response(self, response: str) -> str:
        """Clean up and enhance the AI response"""
        # Remove common artifacts
        response = response.strip()
        
        # Remove redundant prefixes that models sometimes add
        prefixes_to_remove = ["Assistant:", "Response:", "Identra:", "AI:"]
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        return response

    async def _get_available_models(self) -> List[str]:
        """Get list of locally available Ollama models"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse ollama list output
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = [line.split()[0] for line in lines if line.strip()]
                return models
            else:
                logger.warning("Could not list Ollama models")
                return []
                
        except Exception as e:
            logger.warning(f"Failed to check available models: {e}")
            return []

    def _handle_ai_error(self, error: Exception) -> str:
        """Provide helpful error messages for different AI failures"""
        error_str = str(error).lower()
        
        if "connect" in error_str or "connection" in error_str:
            return "❌ Cannot connect to Ollama. Please start it: ollama serve"
        elif "not found" in error_str:
            return f"❌ Model {self.LOCAL_MODEL} not available. Install it: ollama pull {self.LOCAL_MODEL}"
        elif "memory" in error_str or "out of memory" in error_str:
            return f"❌ Insufficient memory for {self.LOCAL_MODEL}. Try a smaller model or close other applications."
        elif "timeout" in error_str:
            return "❌ AI response timed out. The model might be too large for your system."
        else:
            logger.error(f"Unexpected AI error: {error}")
            return f"❌ AI generation failed: {str(error)}"

    async def build_context_pack(
        self,
        conversation_blocks: List[str],
        conversation_type: str,
        target_llm: str = "claude",
        user_id: str = None
    ) -> Dict:
        """Build context pack for LLM consumption"""
        if not self._initialized:
            await self.initialize()
        
        summary = f"Context from {len(conversation_blocks)} blocks"
        
        return {
            "context_pack": {
                "context_type": "conversation_memory",
                "conversation_metadata": {
                    "type": conversation_type,
                    "participants": [user_id] if user_id else ["user"],
                    "block_count": len(conversation_blocks)
                },
                "memory_content": {
                    "summary": summary,
                    "key_points": [f"Context from {conversation_type}"]
                }
            },
            "llm_injection_format": summary,
            "compression_ratio": 0.5
        }