"""
Multi-Model AI Router - Intelligent Model Selection

Routes conversations to optimal AI models based on:
- Message complexity and type
- User preferences and history  
- Model availability and performance
- Cost optimization
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from enum import Enum
import re
from datetime import datetime

logger = logging.getLogger("model_router")

class ModelProvider(str, Enum):
    LOCAL_OLLAMA = "local_ollama"
    ANTHROPIC_CLAUDE = "claude"
    OPENAI_GPT = "gpt"
    GOOGLE_GEMINI = "gemini"

class ConversationType(str, Enum):
    CODING = "coding"
    CREATIVE_WRITING = "creative_writing"
    RESEARCH = "research"
    CASUAL = "casual"
    TECHNICAL_SUPPORT = "technical_support"
    PERSONAL = "personal"

class ModelCapability(BaseModel):
    """Defines what each model is good at"""
    provider: ModelProvider
    model_name: str
    strengths: List[ConversationType]
    max_tokens: int
    cost_per_1k_tokens: float
    avg_response_time_ms: float
    privacy_level: str  # "local", "encrypted", "standard"

class ModelRoutingDecision(BaseModel):
    """Result of routing analysis"""
    selected_provider: ModelProvider
    selected_model: str
    confidence_score: float
    reasoning: str
    fallback_options: List[ModelProvider]
    estimated_cost: float
    estimated_response_time_ms: float

class ConversationContext(BaseModel):
    """Context for routing decisions"""
    message: str
    user_id: str
    conversation_type: ConversationType
    message_length: int
    complexity_indicators: Dict[str, float]
    user_preferences: Dict[str, Any]
    conversation_history_length: int

class ModelRouter:
    """
    Intelligent AI model router for Identra Brain Service
    """
    
    def __init__(self):
        """Initialize router with model capabilities"""
        
        # Model registry with capabilities
        self.model_registry = {
            ModelProvider.LOCAL_OLLAMA: ModelCapability(
                provider=ModelProvider.LOCAL_OLLAMA,
                model_name="llama3.1",
                strengths=[ConversationType.CODING, ConversationType.TECHNICAL_SUPPORT, ConversationType.CASUAL],
                max_tokens=8192,
                cost_per_1k_tokens=0.0,  # Free local processing
                avg_response_time_ms=2000,
                privacy_level="local"
            ),
            ModelProvider.ANTHROPIC_CLAUDE: ModelCapability(
                provider=ModelProvider.ANTHROPIC_CLAUDE,
                model_name="claude-3-sonnet-20240229",
                strengths=[ConversationType.RESEARCH, ConversationType.CODING, ConversationType.TECHNICAL_SUPPORT],
                max_tokens=200000,
                cost_per_1k_tokens=0.003,
                avg_response_time_ms=1500,
                privacy_level="encrypted"
            ),
            ModelProvider.OPENAI_GPT: ModelCapability(
                provider=ModelProvider.OPENAI_GPT,
                model_name="gpt-4-turbo-preview",
                strengths=[ConversationType.CREATIVE_WRITING, ConversationType.CASUAL, ConversationType.RESEARCH],
                max_tokens=128000,
                cost_per_1k_tokens=0.01,
                avg_response_time_ms=1800,
                privacy_level="encrypted"
            ),
            ModelProvider.GOOGLE_GEMINI: ModelCapability(
                provider=ModelProvider.GOOGLE_GEMINI,
                model_name="gemini-1.5-pro",
                strengths=[ConversationType.RESEARCH, ConversationType.CREATIVE_WRITING],
                max_tokens=1000000,
                cost_per_1k_tokens=0.0035,
                avg_response_time_ms=2200,
                privacy_level="standard"
            )
        }
        
        # Routing rules and weights
        self.routing_weights = {
            "conversation_type_match": 0.4,
            "privacy_preference": 0.25,
            "cost_sensitivity": 0.15,
            "response_time_priority": 0.1,
            "user_preference": 0.1
        }
        
        # Performance tracking
        self.model_performance_history: Dict[ModelProvider, List[float]] = {
            provider: [] for provider in ModelProvider
        }
        
    async def route_conversation(
        self,
        message: str,
        user_id: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        conversation_history_length: int = 0
    ) -> ModelRoutingDecision:
        """
        Main routing method - selects optimal model for conversation
        
        Args:
            message: User's input message
            user_id: Unique user identifier
            user_preferences: User's model preferences and settings
            conversation_history_length: Length of current conversation
            
        Returns:
            ModelRoutingDecision with selected model and reasoning
        """
        
        # Step 1: Analyze conversation context
        context = await self._analyze_conversation_context(
            message, user_id, user_preferences or {}, conversation_history_length
        )
        
        # Step 2: Score all available models
        model_scores = await self._score_models(context)
        
        # Step 3: Apply routing rules and select best model
        decision = await self._make_routing_decision(model_scores, context)
        
        # Step 4: Log decision for performance tracking
        await self._log_routing_decision(decision, context)
        
        return decision
    
    async def _analyze_conversation_context(
        self,
        message: str,
        user_id: str,
        user_preferences: Dict[str, Any],
        conversation_history_length: int
    ) -> ConversationContext:
        """Analyze message to understand routing context"""
        
        # Detect conversation type
        conversation_type = await self._detect_conversation_type(message)
        
        # Calculate complexity indicators
        complexity_indicators = {
            "technical_density": self._calculate_technical_density(message),
            "creative_elements": self._calculate_creative_elements(message),
            "research_intent": self._calculate_research_intent(message),
            "code_presence": self._calculate_code_presence(message),
            "length_complexity": len(message) / 1000.0  # Normalized length
        }
        
        return ConversationContext(
            message=message,
            user_id=user_id,
            conversation_type=conversation_type,
            message_length=len(message),
            complexity_indicators=complexity_indicators,
            user_preferences=user_preferences,
            conversation_history_length=conversation_history_length
        )
    
    async def _detect_conversation_type(self, message: str) -> ConversationType:
        """Classify conversation type using pattern matching"""
        
        message_lower = message.lower()
        
        # Coding patterns
        code_patterns = [
            r'\bfunction\b', r'\bclass\b', r'\bdef\b', r'\bimport\b',
            r'```', r'\bcode\b', r'\bbug\b', r'\berror\b', r'\bdebug\b'
        ]
        if any(re.search(pattern, message_lower) for pattern in code_patterns):
            return ConversationType.CODING
        
        # Creative writing patterns  
        creative_patterns = [
            r'\bwrite\b', r'\bstory\b', r'\bpoem\b', r'\bcreative\b',
            r'\bnovel\b', r'\bcharacter\b', r'\bplot\b'
        ]
        if any(re.search(pattern, message_lower) for pattern in creative_patterns):
            return ConversationType.CREATIVE_WRITING
        
        # Research patterns
        research_patterns = [
            r'\bresearch\b', r'\bexplain\b', r'\bwhat is\b', r'\bhow does\b',
            r'\banalyz\b', r'\bcompare\b', r'\bstudy\b'
        ]
        if any(re.search(pattern, message_lower) for pattern in research_patterns):
            return ConversationType.RESEARCH
        
        # Technical support patterns
        tech_patterns = [
            r'\bhelp\b', r'\bproblem\b', r'\bissue\b', r'\btroubleshoot\b',
            r'\bfix\b', r'\bsupport\b'
        ]
        if any(re.search(pattern, message_lower) for pattern in tech_patterns):
            return ConversationType.TECHNICAL_SUPPORT
        
        # Personal patterns
        personal_patterns = [
            r'\bmy name\b', r'\bi am\b', r'\bpersonal\b', r'\bbuilding identra\b'
        ]
        if any(re.search(pattern, message_lower) for pattern in personal_patterns):
            return ConversationType.PERSONAL
        
        return ConversationType.CASUAL
    
    def _calculate_technical_density(self, message: str) -> float:
        """Calculate how technical/complex the message is"""
        technical_terms = [
            'algorithm', 'database', 'api', 'architecture', 'optimization',
            'integration', 'protocol', 'encryption', 'authentication'
        ]
        
        words = message.lower().split()
        technical_count = sum(1 for word in words if word in technical_terms)
        return min(technical_count / max(len(words), 1), 1.0)
    
    def _calculate_creative_elements(self, message: str) -> float:
        """Calculate creative writing indicators"""
        creative_indicators = [
            'imagine', 'create', 'story', 'character', 'narrative',
            'artistic', 'design', 'creative', 'innovative'
        ]
        
        words = message.lower().split()
        creative_count = sum(1 for word in words if word in creative_indicators)
        return min(creative_count / max(len(words), 1), 1.0)
    
    def _calculate_research_intent(self, message: str) -> float:
        """Calculate research/factual query indicators"""
        question_indicators = ['what', 'how', 'why', 'when', 'where', 'explain', 'describe']
        
        message_lower = message.lower()
        question_count = sum(1 for indicator in question_indicators if indicator in message_lower)
        
        # Also check for question marks
        if '?' in message:
            question_count += 1
            
        return min(question_count / 3.0, 1.0)  # Normalize
    
    def _calculate_code_presence(self, message: str) -> float:
        """Calculate code/programming content indicators"""
        if '```' in message or 'function(' in message or 'class ' in message:
            return 1.0
        elif any(keyword in message.lower() for keyword in ['code', 'programming', 'syntax', 'compile']):
            return 0.7
        else:
            return 0.0
    
    async def _score_models(self, context: ConversationContext) -> Dict[ModelProvider, float]:
        """Score each model for the given context"""
        
        scores = {}
        
        for provider, capability in self.model_registry.items():
            score = 0.0
            
            # 1. Conversation type match scoring
            if context.conversation_type in capability.strengths:
                score += self.routing_weights["conversation_type_match"]
            
            # 2. Privacy scoring (higher for local models if privacy is important)
            privacy_preference = context.user_preferences.get("privacy_priority", 0.5)
            if capability.privacy_level == "local":
                score += self.routing_weights["privacy_preference"] * privacy_preference
            elif capability.privacy_level == "encrypted":
                score += self.routing_weights["privacy_preference"] * privacy_preference * 0.7
            
            # 3. Cost sensitivity scoring
            cost_sensitivity = context.user_preferences.get("cost_sensitivity", 0.3)
            if capability.cost_per_1k_tokens == 0.0:  # Free local models
                score += self.routing_weights["cost_sensitivity"] * cost_sensitivity
            else:
                # Lower cost gets higher score
                cost_score = max(0, 1.0 - (capability.cost_per_1k_tokens / 0.01))
                score += self.routing_weights["cost_sensitivity"] * cost_sensitivity * cost_score
            
            # 4. Response time priority
            speed_priority = context.user_preferences.get("speed_priority", 0.5)
            # Normalize response time (lower is better)
            speed_score = max(0, 1.0 - (capability.avg_response_time_ms / 3000))
            score += self.routing_weights["response_time_priority"] * speed_priority * speed_score
            
            # 5. User preference override
            preferred_model = context.user_preferences.get("preferred_model")
            if preferred_model == provider.value:
                score += self.routing_weights["user_preference"]
            
            # 6. Context length considerations
            estimated_tokens = context.message_length / 4  # Rough estimate
            if estimated_tokens > capability.max_tokens * 0.8:  # Too close to limit
                score *= 0.5  # Penalize
            
            scores[provider] = min(score, 1.0)  # Cap at 1.0
        
        return scores
    
    async def _make_routing_decision(
        self,
        model_scores: Dict[ModelProvider, float],
        context: ConversationContext
    ) -> ModelRoutingDecision:
        """Make final routing decision based on scores"""
        
        # Sort models by score
        sorted_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_models:
            # Fallback to local model
            selected_provider = ModelProvider.LOCAL_OLLAMA
            confidence = 0.5
            reasoning = "Fallback to local model - no other models scored"
        else:
            selected_provider, top_score = sorted_models[0]
            confidence = top_score
            
            # Generate reasoning
            capability = self.model_registry[selected_provider]
            reasons = []
            
            if context.conversation_type in capability.strengths:
                reasons.append(f"optimal for {context.conversation_type.value}")
            if capability.privacy_level == "local":
                reasons.append("maximum privacy (local processing)")
            if capability.cost_per_1k_tokens == 0.0:
                reasons.append("zero cost")
            
            reasoning = f"Selected {selected_provider.value}: " + ", ".join(reasons)
        
        # Prepare fallback options
        fallback_options = [provider for provider, _ in sorted_models[1:3]]
        
        # Estimate costs and timing
        capability = self.model_registry[selected_provider]
        estimated_tokens = context.message_length / 4
        estimated_cost = (estimated_tokens / 1000) * capability.cost_per_1k_tokens
        estimated_response_time = capability.avg_response_time_ms
        
        return ModelRoutingDecision(
            selected_provider=selected_provider,
            selected_model=capability.model_name,
            confidence_score=confidence,
            reasoning=reasoning,
            fallback_options=fallback_options,
            estimated_cost=estimated_cost,
            estimated_response_time_ms=estimated_response_time
        )
    
    async def _log_routing_decision(
        self,
        decision: ModelRoutingDecision,
        context: ConversationContext
    ):
        """Log routing decision for performance tracking"""
        logger.info(
            f"Routed {context.conversation_type.value} conversation "
            f"(user: {context.user_id}) to {decision.selected_provider.value} "
            f"(confidence: {decision.confidence_score:.2f})"
        )
    
    async def update_model_performance(
        self,
        provider: ModelProvider,
        actual_response_time_ms: float,
        success: bool
    ):
        """Update model performance metrics for better routing"""
        if success:
            self.model_performance_history[provider].append(actual_response_time_ms)
            
            # Keep only last 100 measurements
            if len(self.model_performance_history[provider]) > 100:
                self.model_performance_history[provider] = self.model_performance_history[provider][-100:]
            
            # Update average response time
            if self.model_performance_history[provider]:
                avg_time = sum(self.model_performance_history[provider]) / len(self.model_performance_history[provider])
                self.model_registry[provider].avg_response_time_ms = avg_time
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available models with their capabilities"""
        return {
            provider.value: {
                "model_name": capability.model_name,
                "strengths": [strength.value for strength in capability.strengths],
                "privacy_level": capability.privacy_level,
                "cost_per_1k_tokens": capability.cost_per_1k_tokens,
                "max_tokens": capability.max_tokens
            }
            for provider, capability in self.model_registry.items()
        }
