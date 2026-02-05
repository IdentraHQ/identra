#!/usr/bin/env python3
"""
Test the Universal Memory Manager with Signal Extractor integration.
Tests signal-based memory retrieval and storage functionality.
"""

import sys
import os

# Add src to Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_memory_system():
    """Test the complete memory system with signal extraction and storage."""
    
    print("\n🧠 Testing Universal Memory System")
    print("=" * 50)
    
    # Import after path setup
    from src.engine.universal_signal_extractor import UniversalSignalExtractor
    from src.engine.universal_memory_manager import UniversalMemoryManager
    
    # Initialize components
    print("📡 Initializing Signal Extractor...")
    extractor = UniversalSignalExtractor()
    
    print("💾 Initializing Memory Manager...")  
    manager = UniversalMemoryManager()
    
    session_id = "test_session_001"
    
    # Test conversation sequence
    conversations = [
        "I'm having trouble with the AuthController API, it keeps returning 401 errors",
        "The JWT token validation seems to be failing in the middleware",
        "Can you help me debug the authentication flow?",
        "I need to book a flight to Tokyo next week",
        "Looking for hotels near Shibuya with good reviews",
        "The database connection is timing out on large queries"
    ]
    
    print(f"\n💬 Processing {len(conversations)} conversations...")
    print("-" * 30)
    
    # Store conversations and extract signals
    stored_interactions = []
    for i, text in enumerate(conversations):
        # Extract signals
        signals = extractor.extract_signals(text, conversation_history=[])
        
        print(f"\n📝 Message {i+1}: '{text[:50]}...'")
        print(f"   🎯 Type: {signals['conversation_type']}, Theme: {signals['theme']}")
        print(f"   🏷️  Entities: {signals['entities']}")
        
        # Store interaction
        interaction_id = f"interaction_{i+1}"
        manager.store_interaction(
            session_id=session_id,
            interaction_id=interaction_id,
            user_text=text,
            assistant_response=f"Response to: {text[:30]}...",
            signals=signals
        )
        stored_interactions.append(interaction_id)
    
    print(f"\n✅ Stored {len(stored_interactions)} interactions")
    
    # Test retrieval scenarios
    test_queries = [
        "Help me with AuthController debugging",
        "Database performance issues", 
        "Planning Tokyo travel"
    ]
    
    print(f"\n🔍 Testing Memory Retrieval")
    print("-" * 30)
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        
        # Extract signals for query
        query_signals = extractor.extract_signals(query, conversation_history=[])
        print(f"   Query signals - Type: {query_signals['conversation_type']}, Entities: {query_signals['entities']}")
        
        # Retrieve relevant context
        context = manager.retrieve_context(session_id, query_signals, max_results=3)
        
        print(f"   📚 Found {len(context)} relevant memories:")
        for memory in context:
            score = memory.get('relevance_score', 0)
            entities = memory['metadata']['entities']
            text = memory['user_text'][:60]
            print(f"      • Score: {score:.3f} | Entities: {entities} | Text: '{text}...'")
    
    print(f"\n🎉 Memory system test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_memory_system()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)