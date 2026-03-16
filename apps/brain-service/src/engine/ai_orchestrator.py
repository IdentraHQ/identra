"""
src/engine/ai_orchestrator.py

Universal AI Orchestrator for Identra Brain-Service.
Combines signal extraction, layered memory retrieval, and multi-model AI routing
to provide context-aware responses.

Key Features:
- Multi-Model Routing (Claude for reasoning, OpenAI for code, Gemini for analysis)  
- Layered Memory System (Long/Medium/Fresh memory from context-package-engine patterns)
- Context Injection with relevance scoring
- Signal-based Model Selection
- Response processing and memory storage

Architecture inspired by:
- mem0ai/mem0: Memory management patterns
- moltbot/moltbot: Multi-model orchestration  
- context-package-engine: Memory layering and scoring
"""

import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import asyncio

# AI Provider imports
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Local SLM integration
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Identra Summarizer Service
try:
    from ..ai.summarizer_service import SummarizerService
    SUMMARIZER_AVAILABLE = True
except ImportError:
    SUMMARIZER_AVAILABLE = False

# Identra engines
from .universal_signal_extractor import UniversalSignalExtractor
from .universal_memory_manager import UniversalMemoryManager

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    """AI Model Provider Selection"""
    CLAUDE = "claude"
    OPENAI = "openai" 
    GEMINI = "gemini"
    SLM_LOCAL = "slm_local"  # Local SLM for summarization
    FALLBACK = "fallback"

class MemoryLayer(Enum):
    """Memory Layer Types (from context-package-engine patterns)"""
    FRESH = "fresh"      # Current session, immediate context
    MEDIUM = "medium"    # Recent sessions, related topics  
    LONG = "long"        # Historical context, deep patterns

class AIOrchestrator:
    """
    Core AI orchestration engine that combines signal extraction, 
    layered memory retrieval, and multi-model AI routing.
    
    Handles the complete conversation flow:
    User Input → Signal Extraction → Memory Layering → Model Selection → Response Generation → Memory Storage
    """
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize the AI Orchestrator with available providers.
        
        Args:
            api_keys: Dict with keys: anthropic_key, openai_key, gemini_key
        """
        self.api_keys = api_keys or {}
        
        # Initialize engines
        self.signal_extractor = UniversalSignalExtractor()
        self.memory_manager = UniversalMemoryManager()
        
        # Initialize AI clients
        self._init_ai_clients()
        
        # Model selection rules (from signal analysis)
        self.model_selection_rules = {
            "TECHNICAL_HELP": {
                "primary": ModelProvider.CLAUDE,    # Best for reasoning
                "fallback": ModelProvider.OPENAI
            },
            "CODE_REVIEW": {
                "primary": ModelProvider.OPENAI,    # Best for code
                "fallback": ModelProvider.CLAUDE
            },
            "DATA_ANALYSIS": {
                "primary": ModelProvider.GEMINI,    # Best for analysis
                "fallback": ModelProvider.CLAUDE
            },
            "GENERAL_CHAT": {
                "primary": ModelProvider.CLAUDE,    # Best overall
                "fallback": ModelProvider.OPENAI
            },
            "CREATIVE": {
                "primary": ModelProvider.CLAUDE,    # Best for creativity
                "fallback": ModelProvider.OPENAI
            },
            "SUMMARIZATION": {
                "primary": ModelProvider.SLM_LOCAL,   # Local SLM for privacy
                "fallback": ModelProvider.CLAUDE
            },
            "CONTENT_SUMMARY": {
                "primary": ModelProvider.SLM_LOCAL,   # Keep summaries local
                "fallback": ModelProvider.OPENAI
            }
        }
        
        logger.info(f"AI Orchestrator initialized with providers: {self._get_available_providers()}")

    def _init_ai_clients(self):
        """Initialize AI provider clients"""
        self.clients = {}
        
        # Claude (Anthropic)
        if ANTHROPIC_AVAILABLE and self.api_keys.get('anthropic_key'):
            try:
                self.clients[ModelProvider.CLAUDE] = anthropic.Anthropic(
                    api_key=self.api_keys['anthropic_key']
                )
                logger.info("✅ Claude client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude: {e}")
        
        # OpenAI
        if OPENAI_AVAILABLE and self.api_keys.get('openai_key'):
            try:
                self.clients[ModelProvider.OPENAI] = openai.OpenAI(
                    api_key=self.api_keys['openai_key']
                )
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")
        
        # Gemini
        if GEMINI_AVAILABLE and self.api_keys.get('gemini_key'):
            try:
                genai.configure(api_key=self.api_keys['gemini_key'])
                self.clients[ModelProvider.GEMINI] = genai.GenerativeModel('gemini-pro')
                logger.info("✅ Gemini client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Local SLM (Summarizer Service Integration)
        if SUMMARIZER_AVAILABLE:
            try:
                # Initialize the working summarizer service
                self.clients[ModelProvider.SLM_LOCAL] = SummarizerService()
                logger.info("✅ Local SLM (Summarizer) initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize local SLM: {e}")
        elif OLLAMA_AVAILABLE:
            try:
                # Fallback to direct ollama if summarizer service unavailable
                models = ollama.list()
                available_models = [m['name'] for m in models.get('models', [])]
                
                # Prefer llama3.1 or mistral for summarization
                summarization_models = ['llama3.1:latest', 'llama3.1', 'mistral:7b']
                selected_model = None
                
                for model in summarization_models:
                    if model in available_models:
                        selected_model = model
                        break
                
                if selected_model:
                    self.clients[ModelProvider.SLM_LOCAL] = {
                        'client': ollama,
                        'model': selected_model,
                        'type': 'direct_ollama'
                    }
                    logger.info(f"✅ Direct Ollama SLM initialized: {selected_model}")
                else:
                    logger.warning("No suitable Ollama models found for local SLM")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama SLM: {e}")

    def _get_available_providers(self) -> List[str]:
        """Get list of available AI providers"""
        return [provider.value for provider in self.clients.keys()]

    async def process_conversation(
        self, 
        session_id: str, 
        user_input: str, 
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Main conversation processing pipeline.
        
        Flow:
        1. Extract signals from user input
        2. Retrieve layered memory context 
        3. Select optimal AI model
        4. Generate context-aware response
        5. Store interaction in memory
        
        Returns:
            {
                "response": str,
                "model_used": str,
                "context_layers": dict,
                "signals": dict,
                "processing_time": float
            }
        """
        start_time = time.time()
        
        try:
            # 1. SIGNAL EXTRACTION
            logger.info(f"🔍 Extracting signals for: '{user_input[:50]}...'")
            signals = self.signal_extractor.extract_signals(
                user_input, 
                conversation_history or []
            )
            
            # 2. LAYERED MEMORY RETRIEVAL (using context-package-engine patterns)
            logger.info(f"🧠 Retrieving layered memory context...")
            context_layers = await self._retrieve_layered_context(session_id, signals)
            
            # 3. MODEL SELECTION (based on signals)
            selected_model = self._select_model(signals)
            logger.info(f"🤖 Selected model: {selected_model.value}")
            
            # 4. CONTEXT-AWARE RESPONSE GENERATION
            response = await self._generate_response(
                user_input, signals, context_layers, selected_model
            )
            
            # 5. MEMORY STORAGE
            logger.info(f"💾 Storing interaction in memory...")
            self.memory_manager.store_interaction(
                session_id, user_input, response, signals
            )
            
            processing_time = time.time() - start_time
            
            return {
                "response": response,
                "model_used": selected_model.value,
                "context_layers": {
                    "fresh_count": len(context_layers.get("fresh", [])),
                    "medium_count": len(context_layers.get("medium", [])),
                    "long_count": len(context_layers.get("long", []))
                },
                "signals": signals,
                "processing_time": round(processing_time * 1000, 2)  # ms
            }
            
        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            return {
                "response": "I'm having trouble processing your request right now. Please try again.",
                "model_used": "error",
                "context_layers": {},
                "signals": {},
                "processing_time": time.time() - start_time,
                "error": str(e)
            }

    async def _retrieve_layered_context(
        self, 
        session_id: str, 
        signals: Dict[str, Any]
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve context using layered memory approach from context-package-engine.
        
        Memory Layers:
        - FRESH: Current session, immediate context (last 5 interactions)
        - MEDIUM: Recent sessions, related topics (last 2 days, similar entities)
        - LONG: Historical patterns, deep context (similar themes, user patterns)
        """
        context_layers = {
            "fresh": [],
            "medium": [], 
            "long": []
        }
        
        try:
            # FRESH MEMORY: Current session context
            fresh_signals = signals.copy()
            fresh_signals['memory_scope'] = 'RECENT_SESSION'
            fresh_context = self.memory_manager.retrieve_context(
                session_id, fresh_signals, limit=5
            )
            context_layers["fresh"] = fresh_context
            
            # MEDIUM MEMORY: Related recent context (entity-based)
            if signals.get('key_entities'):
                medium_signals = {
                    'key_entities': signals.get('key_entities', []),
                    'context_theme': signals.get('context_theme'),
                    'memory_scope': 'RELATED_TOPICS'
                }
                medium_context = self.memory_manager.retrieve_context(
                    session_id, medium_signals, limit=3
                )
                # Filter out fresh memories to avoid duplication
                medium_context = [
                    ctx for ctx in medium_context 
                    if ctx not in fresh_context
                ]
                context_layers["medium"] = medium_context
            
            # LONG MEMORY: Historical patterns (theme-based)
            long_signals = {
                'context_theme': signals.get('context_theme'),
                'conversation_type': signals.get('conversation_type'),
                'memory_scope': 'FULL_CONTEXT'
            }
            long_context = self.memory_manager.retrieve_context(
                session_id, long_signals, limit=2
            )
            # Filter out already retrieved memories
            existing_contexts = fresh_context + context_layers["medium"]
            long_context = [
                ctx for ctx in long_context 
                if ctx not in existing_contexts
            ]
            context_layers["long"] = long_context
            
            logger.info(
                f"📚 Retrieved context layers: "
                f"Fresh({len(context_layers['fresh'])}), "
                f"Medium({len(context_layers['medium'])}), "
                f"Long({len(context_layers['long'])})"
            )
            
        except Exception as e:
            logger.error(f"Error retrieving layered context: {e}")
        
        return context_layers

    def _select_model(self, signals: Dict[str, Any]) -> ModelProvider:
        """
        Select the best AI model based on conversation signals.
        
        Selection logic:
        - TECHNICAL_HELP → Claude (best reasoning)
        - CODE_REVIEW → OpenAI (best for code)
        - DATA_ANALYSIS → Gemini (best for analysis)
        - Default → Claude (best overall)
        """
        conversation_type = signals.get('conversation_type', 'GENERAL_CHAT')
        
        # Get model selection rule
        selection_rule = self.model_selection_rules.get(
            conversation_type, 
            self.model_selection_rules['GENERAL_CHAT']
        )
        
        primary_model = selection_rule['primary']
        fallback_model = selection_rule['fallback']
        
        # Check if primary model is available
        if primary_model in self.clients:
            return primary_model
        elif fallback_model in self.clients:
            logger.warning(f"Primary model {primary_model.value} unavailable, using fallback {fallback_model.value}")
            return fallback_model
        else:
            # Use any available model
            if self.clients:
                available_model = list(self.clients.keys())[0]
                logger.warning(f"Using available model: {available_model.value}")
                return available_model
            else:
                logger.error("No AI models available")
                return ModelProvider.FALLBACK

    async def _generate_response(
        self,
        user_input: str,
        signals: Dict[str, Any],
        context_layers: Dict[str, List[Dict]], 
        model: ModelProvider
    ) -> str:
        """Generate AI response with injected context"""
        
        if model == ModelProvider.FALLBACK:
            return "I'm currently unable to process your request. Please check your AI provider configuration."
        
        # Build context-aware prompt
        context_prompt = self._build_context_prompt(user_input, context_layers, signals)
        
        try:
            if model == ModelProvider.CLAUDE:
                return await self._call_claude(context_prompt)
            elif model == ModelProvider.OPENAI:
                return await self._call_openai(context_prompt)
            elif model == ModelProvider.GEMINI:
                return await self._call_gemini(context_prompt)
            elif model == ModelProvider.SLM_LOCAL:
                return await self._call_local_slm(user_input, signals, context_layers)
            else:
                return "Model not configured properly."
                
        except Exception as e:
            logger.error(f"Error generating response with {model.value}: {e}")
            return f"I encountered an error while processing your request. Please try again."

    def _build_context_prompt(
        self, 
        user_input: str, 
        context_layers: Dict[str, List[Dict]], 
        signals: Dict[str, Any]
    ) -> str:
        """
        Build context-aware prompt using layered memory.
        Follows context-package-engine patterns for memory injection.
        """
        prompt_parts = []
        
        # System context
        prompt_parts.append(
            "You are Identra AI, a helpful assistant with access to conversation history. "
            "Use the provided context to give relevant, personalized responses."
        )
        
        # Add layered context (prioritize fresh > medium > long)
        if context_layers.get("fresh"):
            prompt_parts.append("\n=== RECENT CONTEXT ===")
            for ctx in context_layers["fresh"][-3:]:  # Last 3 fresh memories
                prompt_parts.append(f"User: {ctx['user_text']}")
                prompt_parts.append(f"Assistant: {ctx['assistant_response']}")
        
        if context_layers.get("medium"):
            prompt_parts.append("\n=== RELATED CONTEXT ===")
            for ctx in context_layers["medium"][:2]:  # Top 2 medium memories
                prompt_parts.append(f"Previous: {ctx['user_text']} → {ctx['assistant_response']}")
        
        if context_layers.get("long"):
            prompt_parts.append("\n=== BACKGROUND CONTEXT ===")
            for ctx in context_layers["long"][:1]:  # Top 1 long memory
                prompt_parts.append(f"Historical: {ctx['user_text']}")
        
        # Current user input
        prompt_parts.append(f"\n=== CURRENT REQUEST ===")
        prompt_parts.append(f"User: {user_input}")
        prompt_parts.append("\nAssistant:")
        
        return "\n".join(prompt_parts)

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API"""
        try:
            message = self.clients[ModelProvider.CLAUDE].messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            response = self.clients[ModelProvider.OPENAI].chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API"""
        try:
            response = self.clients[ModelProvider.GEMINI].generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def _call_local_slm(
        self, 
        user_input: str, 
        signals: Dict[str, Any], 
        context_layers: Dict[str, List[Dict]]
    ) -> str:
        """Call Local SLM using the integrated Summarizer Service"""
        try:
            client = self.clients[ModelProvider.SLM_LOCAL]
            
            # Check if we have the SummarizerService or direct ollama
            if isinstance(client, SummarizerService):
                # Use the production summarizer service
                conversation_type = signals.get('conversation_type', 'GENERAL_CHAT')
                
                if conversation_type in ['SUMMARIZATION', 'CONTENT_SUMMARY']:
                    # Direct summarization request
                    from ..ai.Summarizer_service import SummarizationRequest, SummarizationOptions
                    
                    request = SummarizationRequest(
                        text=user_input,
                        options=SummarizationOptions(
                            model="llama3.1",
                            format="bullet_points",
                            technical_accuracy=True,
                            privacy_mode=True
                        )
                    )
                    response = await client.summarize(request)
                    return response.summary
                else:
                    # General conversation - build context-aware prompt
                    context_prompt = self._build_context_prompt(user_input, context_layers, signals)
                    
                    # Use direct ollama call for conversation
                    import ollama
                    response = ollama.chat(
                        model="llama3.1",
                        messages=[
                            {'role': 'system', 'content': 'You are Identra AI, a helpful assistant.'},
                            {'role': 'user', 'content': context_prompt}
                        ],
                        options={'temperature': 0.7, 'num_ctx': 8192}
                    )
                    return response['message']['content']
                    
            elif isinstance(client, dict) and client.get('type') == 'direct_ollama':
                # Direct ollama fallback
                context_prompt = self._build_context_prompt(user_input, context_layers, signals)
                
                response = client['client'].chat(
                    model=client['model'],
                    messages=[
                        {'role': 'system', 'content': 'You are Identra AI, a helpful assistant.'},
                        {'role': 'user', 'content': context_prompt}
                    ],
                    options={'temperature': 0.7}
                )
                return response['message']['content']
            else:
                return "Local SLM not properly configured."
                
        except Exception as e:
            logger.error(f"Local SLM error: {e}")
            raise

    async def summarize_content(self, content: str, session_id: str = "summary") -> Dict[str, Any]:
        """
        Public method for direct content summarization using local SLM.
        Integrates with the main orchestrator flow.
        """
        start_time = time.time()
        
        try:
            # Force summarization by setting conversation type
            signals = {
                'conversation_type': 'SUMMARIZATION',
                'context_theme': 'CONTENT_ANALYSIS',
                'key_entities': [],
                'conversation_state': 'SINGLE_REQUEST'
            }
            
            # Use local SLM for summarization
            if ModelProvider.SLM_LOCAL in self.clients:
                response = await self._call_local_slm(content, signals, {'fresh': [], 'medium': [], 'long': []})
                
                return {
                    "summary": response,
                    "model_used": "slm_local",
                    "original_length": len(content),
                    "summary_length": len(response),
                    "compression_ratio": round(len(response) / len(content), 2),
                    "processing_time": round((time.time() - start_time) * 1000, 2)
                }
            else:
                # Fallback to cloud models
                selected_model = self._select_model(signals)
                response = await self._generate_response(
                    f"Please provide a concise summary: {content}",
                    signals,
                    {'fresh': [], 'medium': [], 'long': []},
                    selected_model
                )
                
                return {
                    "summary": response,
                    "model_used": selected_model.value,
                    "original_length": len(content),
                    "summary_length": len(response),
                    "compression_ratio": round(len(response) / len(content), 2),
                    "processing_time": round((time.time() - start_time) * 1000, 2)
                }
                
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                "summary": "Unable to generate summary at this time.",
                "model_used": "error",
                "error": str(e),
                "processing_time": round((time.time() - start_time) * 1000, 2)
            }

# --- Integration Test ---
if __name__ == "__main__":
    async def test_orchestrator():
        """Test the AI Orchestrator without API keys (mock mode)"""
        print("🤖 Testing AI Orchestrator (Mock Mode)")
        print("=" * 50)
        
        # Initialize without API keys (will use fallback)
        orchestrator = AIOrchestrator()
        
        session_id = "test_orchestration"
        user_input = "Help me debug the AuthController timeout issue"
        
        print(f"Input: {user_input}")
        
        # Process conversation
        result = await orchestrator.process_conversation(session_id, user_input)
        
        print(f"\nResult:")
        print(f"- Response: {result['response']}")
        print(f"- Model: {result['model_used']}")
        print(f"- Context Layers: {result['context_layers']}")
        print(f"- Processing Time: {result['processing_time']}ms")
        
        return result
    
    # Run test
    import asyncio
    asyncio.run(test_orchestrator())