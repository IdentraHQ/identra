import sys
import logging
from src.engine.universal_memory_manager import UniversalMemoryManager

# Configure logging to see output clearly
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_test():
    try:
        print("=================================================")
        print("🔄 Testing UniversalMemoryManager...")
        
        # 1. Initialize
        manager = UniversalMemoryManager()
        print("✅ Memory Manager initialized successfully")

        # 2. Mock Data for Storage
        session_id = "test_user_1"
        user_msg = "I need to fix the login API"
        ai_msg = "Let's check the auth logs."
        signals = {
            "conversation_type": "TECHNICAL_HELP",
            "context_theme": "TROUBLESHOOTING",
            "key_entities": ["login", "API"],
            "intent_category": "ACTIONABLE"
        }

        # 3. Store Interaction (CORRECTED LINE)
        # We only pass 4 arguments. The interaction_id is generated automatically inside the class.
        manager.store_interaction(session_id, user_msg, ai_msg, signals)
        print("✅ Interaction stored successfully")

        # 4. Test Retrieval
        print("🔄 Attempting retrieval...")
        retrieval_signals = {
            "key_entities": ["login"],
            "context_theme": "TROUBLESHOOTING",
            "memory_scope": "RECENT_SESSION"
        }
        
        context = manager.retrieve_context(session_id, retrieval_signals)
        
        print(f"✅ Context retrieved: {len(context)} items found.")
        if len(context) > 0:
            print(f"   Last Memory User Text: '{context[0]['user_text']}'")
            print("🎉 SUCCESS: The Universal Memory Manager is working correctly.")
        else:
            print("❌ FAIL: No context was retrieved.")

    except TypeError as e:
        print(f"❌ TYPE ERROR: {e}")
        print("   (This usually means arguments passed to store_interaction don't match the definition)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()