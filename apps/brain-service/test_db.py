from src.engine.memory_store import MemoryStore

def test_database():
    print("🚀 Initializing Memory Store...")
    # This will create 'identra_memory.db' if it doesn't exist
    db = MemoryStore()

    # 1. Save a "Secret" Memory
    print("💾 Saving a test memory...")
    db.save_message(
        conversation_id="test_conv_001", 
        role="user", 
        content="My secret project code is 7788."
    )
    
    # 2. Test Retrieval (Using different words!)
    print("🔍 Testing Retrieval...")
    # Notice: I am asking "What is the project code?", NOT the exact sentence above.
    # The AI must understand the MEANING to find it.
    results = db.retrieve_context("What is the project code?")
    
    print("\n----- SEARCH RESULTS -----")
    if results:
        for r in results:
            print(f"✅ Found Relevant Memory: '{r}'")
    else:
        print("❌ No relevant memories found.")

if __name__ == "__main__":
    test_database()