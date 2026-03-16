"""
src/engine/universal_memory_manager.py

Universal Memory Manager for Identra Brain-Service.
Handles storage and retrieval of conversation context using dynamic signals
rather than hardcoded entity lookups. Integrates with the Vault via Tunnel Gateway.

Capabilities:
- Signal-based Memory Retrieval (Entity overlap, Theme matching)
- Adaptive Scoping (Deep Dive vs Continuation)
- Encrypted Storage Interface (gRPC to Vault)
- In-memory caching for active sessions
"""

import time
import json
import logging
import uuid
from typing import List, Dict, Any, Optional

# Placeholder for gRPC imports - assumes Identra's tunnel-gateway protos exist
# from src.protos import vault_pb2, vault_pb2_grpc
# import grpc

# Configure Logging
logger = logging.getLogger(__name__)

class UniversalMemoryManager:
    """
    Manages conversation history and long-term memory retrieval based on 
    universal signals (Work, Tech, Personal, Creative) rather than just Locations.
    """

    def __init__(self, vault_address: str = "localhost:50051"):
        self.vault_address = vault_address
        # Local in-memory cache for active sessions to reduce latency
        # Structure: {session_id: [List of interaction dicts]}
        self._active_session_cache: Dict[str, List[Dict]] = {}
        
        # Connection state
        self.is_connected = False
        self._connect_to_vault()

    def _connect_to_vault(self):
        """Establish gRPC connection to Identra Tunnel Gateway."""
        try:
            # self.channel = grpc.insecure_channel(self.vault_address)
            # self.stub = vault_pb2_grpc.VaultServiceStub(self.channel)
            self.is_connected = True
            logger.info(f"Connected to Memory Vault at {self.vault_address}")
        except Exception as e:
            logger.error(f"Failed to connect to Memory Vault: {e}")
            self.is_connected = False

    def store_interaction(self, session_id: str, user_message: str, ai_response: str, signals: Dict[str, Any]):
        """
        Stores a complete interaction (User Input + AI Output + Context Signals).
        This data is saved to the active cache AND sent to the encrypted vault.
        """
        interaction_id = str(uuid.uuid4())
        timestamp = time.time()

        memory_entry = {
            "id": interaction_id,
            "timestamp": timestamp,
            "role": "interaction",
            "user_text": user_message,
            "ai_text": ai_response,
            # Store signals to allow "Universal" retrieval later
            "metadata": {
                "type": signals.get("conversation_type"),
                "theme": signals.get("context_theme"),
                "entities": signals.get("key_entities", []),
                "intent": signals.get("intent_category")
            }
        }

        # 1. Update Active Cache
        if session_id not in self._active_session_cache:
            self._active_session_cache[session_id] = []
        self._active_session_cache[session_id].append(memory_entry)

        # 2. Async Persist to Encrypted Vault (Simulated)
        self._persist_to_vault(session_id, memory_entry)

    def retrieve_context(self, session_id: str, current_signals: Dict[str, Any], limit: int = 5) -> List[Dict]:
        """
        The Core Logic: Selects memories based on the 'Universal Signals'.
        Decides whether to fetch Recent History, Deep Dives, or Cross-Topic Context.
        """
        scope = current_signals.get("memory_scope", "RECENT_SESSION")
        state = current_signals.get("conversation_state", "CONTINUATION")
        
        logger.info(f"Retrieving context for Session: {session_id} | Scope: {scope} | State: {state}")

        # A. Get Active Session History (Fast RAM Access)
        recent_history = self._active_session_cache.get(session_id, [])

        # B. Apply Scoping Logic
        if scope == "RECENT_SESSION" or state == "NEW_TOPIC":
            # Just return the tail of the conversation
            return self._format_output(recent_history[-limit:])

        elif scope == "LONG_TERM_PATTERN" or state == "CONTEXT_SWITCH":
            # The user switched topic. We need to check if we discussed this BEFORE.
            # Example: Switched from "Project A" to "Weekend Plans" -> Search for past "Personal" chats.
            vault_results = self._search_vault(session_id, current_signals)
            
            # Combine: Recent context (to keep flow) + Relevant past memories
            combined = recent_history[-2:] + vault_results
            return self._format_output(combined)

        elif scope == "FULL_CONTEXT" or state == "DEEP_DIVE":
            # User is deep diving (e.g., "Debug AuthController"). 
            # We need EVERYTHING related to "AuthController" from this session and past sessions.
            related_memories = self._filter_by_relevance(recent_history, current_signals)
            
            # If we don't have enough locally, ask the vault
            if len(related_memories) < limit:
                vault_results = self._search_vault(session_id, current_signals)
                related_memories.extend(vault_results)
            
            # Sort by relevance score
            related_memories.sort(key=lambda x: x.get("_score", 0), reverse=True)
            return self._format_output(related_memories[:limit])

        # Default fallback
        return self._format_output(recent_history[-limit:])

    def _filter_by_relevance(self, memories: List[Dict], signals: Dict[str, Any]) -> List[Dict]:
        """
        Scores memories based on Entity Overlap and Theme Matching.
        Returns memories with a temporary '_score' field.
        """
        scored_memories = []
        target_entities = set(e.lower() for e in signals.get("key_entities", []))
        target_theme = signals.get("context_theme", "")

        for mem in memories:
            score = 0
            meta = mem.get("metadata", {})
            
            # 1. Entity Overlap Score (High Value)
            mem_entities = set(e.lower() for e in meta.get("entities", []))
            overlap = target_entities.intersection(mem_entities)
            score += len(overlap) * 10  # 10 points per matching entity

            # 2. Theme Match Score (Medium Value)
            if meta.get("theme") == target_theme:
                score += 5

            # 3. Recency Boost (Small Value)
            # Assuming strictly linear list, later items are more recent.
            # Real implementation would use timestamp delta.
            score += 0.1 

            if score > 0:
                mem["_score"] = score
                scored_memories.append(mem)
        
        return scored_memories

    def _search_vault(self, session_id: str, signals: Dict[str, Any]) -> List[Dict]:
        """
        Simulates searching the Encrypted Vault via Tunnel Gateway.
        In a real scenario, this builds a gRPC query using the signals.
        """
        if not self.is_connected:
            return []

        # Logic: "Select * from memories where entities in [signals.entities] OR theme = signals.theme"
        logger.debug(f"Vault Search Query: {signals['key_entities']} in Theme {signals['context_theme']}")
        
        # MOCK RETURN: Simulating a found past memory for demonstration
        # In production, this call goes to `vault-daemon`
        mock_results = []
        
        # Example: If searching for "AuthController", pretend we found an old bug report
        if "AuthController" in signals.get("key_entities", []):
            mock_results.append({
                "id": "old-mem-001",
                "timestamp": time.time() - 86400,
                "role": "interaction",
                "user_text": "I had issues with AuthController latency last week.",
                "ai_text": "We identified a memory leak in the token generation function.",
                "metadata": {"entities": ["AuthController", "latency"], "theme": "TROUBLESHOOTING"},
                "_score": 15
            })
            
        return mock_results

    def _persist_to_vault(self, session_id: str, memory_entry: Dict):
        """
        Sends data to the vault daemon.
        """
        if self.is_connected:
            # request = vault_pb2.StoreRequest(session_id=session_id, payload=json.dumps(memory_entry))
            # self.stub.StoreMemory(request)
            pass

    def _format_output(self, memories: List[Dict]) -> List[Dict]:
        """
        Standardizes output for the Context Builder.
        Removes internal scoring keys and ensures strict formatting.
        """
        formatted = []
        for mem in memories:
            # Strip internal fields like '_score'
            clean_mem = {k: v for k, v in mem.items() if not k.startswith('_')}
            formatted.append(clean_mem)
        return formatted

# --- Integration Test ---
if __name__ == "__main__":
    # Simulate the flow
    manager = UniversalMemoryManager()
    session_id = "user_123"

    # 1. Store a previous technical discussion
    prev_signals = {
        "conversation_type": "TECHNICAL_HELP",
        "context_theme": "TROUBLESHOOTING",
        "key_entities": ["AuthController", "JWT", "API"],
        "intent_category": "ACTIONABLE"
    }
    manager.store_interaction(
        session_id=session_id,
        interaction_id="interaction_1",
        user_text="The JWT tokens are expiring too fast in AuthController.",
        assistant_response="Check the expiration setting in config.py.",
        signals=prev_signals
    )

    # 2. Simulate a DEEP DIVE request (Universal Extractor Output)
    new_signals = {
        "conversation_type": "TECHNICAL_HELP",
        "context_theme": "TROUBLESHOOTING",
        "key_entities": ["AuthController", "debug"],
        "conversation_state": "DEEP_DIVE", # Extractor says we are digging deeper
        "memory_scope": "FULL_CONTEXT"     # We need full history
    }

    print("--- Retrieving Context for Deep Dive ---")
    context = manager.retrieve_context(session_id, new_signals)
    
    for msg in context:
        print(f"Found Memory: {msg['user_text']} (Entities: {msg['metadata']['entities']})")