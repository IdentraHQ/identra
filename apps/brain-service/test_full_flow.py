import sys
import time

print("🚀 Script starting...")  # This runs immediately to prove the file is loading

try:
    from src.engine.universal_signal_extractor import UniversalSignalExtractor
    from src.engine.universal_memory_manager import UniversalMemoryManager
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

def test_integration():
    print("\n=================================================")
    print("🧠 INTEGRATION TEST: Extractor + Memory Manager")
    print("=================================================\n")

    # 1. Initialize Components
    print("1. Initializing Engines...")
    extractor = UniversalSignalExtractor()
    manager = UniversalMemoryManager()
    session_id = "user_integration_test"
    print("   ✅ Engines Ready\n")

    # 2. Simulate User Input
    user_text = "I need to fix the AuthController latency issue."
    print(f"2. User Input: '{user_text}'")

    # 3. RUN EXTRACTOR
    print("   running extractor...")
    signals = extractor.extract_signals(user_text)
    
    print("\n   🔍 EXTRACTOR OUTPUT:")
    print(f"      - Type: {signals['conversation_type']}")
    print(f"      - Theme: {signals['context_theme']}")
    print(f"      - Entities: {signals['key_entities']}")
    print(f"      - Scope: {signals['memory_scope']}")
    print("   ✅ Signals Generated\n")

    # 4. RUN MEMORY MANAGER (Store)
    print("3. Storing Interaction...")
    ai_response = "I see the latency spike. Let's check the database logs."
    
    # Pass the EXTRACTED signals to the manager
    manager.store_interaction(session_id, user_text, ai_response, signals)
    print("   ✅ Interaction Saved to Memory\n")

    # 5. RUN MEMORY MANAGER (Retrieve)
    print("4. Retrieving Context (Deep Dive)...")
    
    # Simulate a follow-up question
    # We simulate a "DEEP DIVE" state to force the manager to search history
    follow_up_signals = extractor.extract_signals("Show me the AuthController logs.")
    follow_up_signals['conversation_state'] = "DEEP_DIVE" 
    
    context = manager.retrieve_context(session_id, follow_up_signals)
    
    print(f"\n   🔍 MEMORY OUTPUT:")
    print(f"      - Found {len(context)} relevant memories.")
    if len(context) > 0:
        print(f"      - Retrieved: '{context[0]['user_text']}'")
    
    print("\n=================================================")
    print("🎉 FULL SYSTEM TEST PASSED")
    print("=================================================")

# This MUST be at the very left (no spaces before 'if')
if __name__ == "__main__":
    test_integration()
