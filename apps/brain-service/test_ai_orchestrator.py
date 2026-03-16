#!/usr/bin/env python3
"""
Test the AI Orchestrator with full integration:
Signal Extraction → Layered Memory → Model Selection → Response Generation
"""

import sys
import asyncio
sys.path.insert(0, 'src')

async def test_ai_orchestrator():
    """Test the complete AI orchestration pipeline"""
    
    print("🤖 AI ORCHESTRATOR INTEGRATION TEST")
    print("=" * 50)
    
    # Import after path setup
    from engine.ai_orchestrator import AIOrchestrator
    
    # Initialize orchestrator (without API keys for testing)
    print("📡 Initializing AI Orchestrator...")
    orchestrator = AIOrchestrator()
    
    # Test conversation flow
    session_id = "orchestrator_test_001"
    conversations = [
        "I need help debugging the AuthController API timeout issues",
        "The JWT validation is failing in the middleware", 
        "Can you show me the database query optimization for user lookup?"
    ]
    
    print(f"\n💬 Processing {len(conversations)} conversations...")
    print("-" * 50)
    
    for i, user_input in enumerate(conversations, 1):
        print(f"\n🔄 Conversation {i}: '{user_input[:60]}...'")
        
        # Process conversation through orchestrator
        result = await orchestrator.process_conversation(session_id, user_input)
        
        print(f"   🤖 Model Selected: {result['model_used']}")
        print(f"   📚 Context Layers: Fresh({result['context_layers']['fresh_count']}), Medium({result['context_layers']['medium_count']}), Long({result['context_layers']['long_count']})")
        print(f"   ⏱️  Processing Time: {result['processing_time']}ms")
        print(f"   💬 Response: '{result['response'][:100]}...'")
        
        # Show signals extracted
        signals = result.get('signals', {})
        print(f"   🎯 Signals: Type={signals.get('conversation_type')}, Theme={signals.get('context_theme')}")
    
    print(f"\n✅ AI Orchestrator test completed successfully!")
    
    # Test model selection logic
    print(f"\n🔍 Testing Model Selection Rules:")
    test_cases = [
        {"conversation_type": "TECHNICAL_HELP", "expected": "claude"},
        {"conversation_type": "CODE_REVIEW", "expected": "openai"},  
        {"conversation_type": "DATA_ANALYSIS", "expected": "gemini"},
        {"conversation_type": "GENERAL_CHAT", "expected": "claude"}
    ]
    
    for test_case in test_cases:
        signals = {"conversation_type": test_case["conversation_type"]}
        selected_model = orchestrator._select_model(signals)
        print(f"   {test_case['conversation_type']} → {selected_model.value} (Expected: {test_case['expected']})")

if __name__ == "__main__":
    asyncio.run(test_ai_orchestrator())