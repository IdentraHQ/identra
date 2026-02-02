# Engine/extractor.py
"""
General-purpose conversation signal extractor.
Extracts entities, topics, and usage patterns from user messages
for cross-agent conversation continuity.
"""

import re
from typing import Dict, List


def extract_signals(user_message: str) -> dict:
    """
    Extract conversation signals from user message.
    Returns structured data for memory storage and retrieval.
    
    Args:
        user_message: Raw user input
        
    Returns:
        dict with: entity, topic, usage_instruction, text_blocks
    """
    message = user_message.lower()
    original_message = user_message
    
    # -------------------------
    # ENTITY EXTRACTION (People, Companies, Projects)
    # -------------------------
    entity = "general"
    
    # Look for people names (capitalized words that might be names)
    potential_names = re.findall(r'\b[A-Z][a-z]+\b', original_message)
    if potential_names:
        entity = potential_names[0]  # Take first name found
    
    # Look for common work entities
    if "team" in message:
        entity = "team"
    elif "client" in message:
        entity = "client"  
    elif "manager" in message or "boss" in message:
        entity = "manager"
    elif "project" in message:
        # Try to extract project name
        project_match = re.search(r'project\s+([a-zA-Z0-9_-]+)', message)
        if project_match:
            entity = f"project_{project_match.group(1)}"
        else:
            entity = "project"

    # -------------------------
    # TOPIC EXTRACTION (Conversation Topics)
    # -------------------------
    topic = "general_chat"
    
    # Work-related topics
    if "meeting" in message:
        topic = "meetings"
    elif "deadline" in message or "due date" in message:
        topic = "task_management"
    elif "budget" in message or "cost" in message:
        topic = "finance"
    elif "timeline" in message or "schedule" in message:
        topic = "planning"
    elif "problem" in message or "issue" in message or "bug" in message:
        topic = "problem_solving"
    elif "idea" in message or "suggestion" in message:
        topic = "brainstorming"
    
    # Personal topics  
    elif "family" in message:
        topic = "personal_family"
    elif "vacation" in message or "travel" in message:
        topic = "personal_travel"
    elif "health" in message or "doctor" in message:
        topic = "personal_health"
    
    # Learning/research topics
    elif "learn" in message or "study" in message or "research" in message:
        topic = "learning"
    elif "tutorial" in message or "guide" in message or "how to" in message:
        topic = "tutorial_request"

    # -------------------------
    # USAGE/INTENT EXTRACTION  
    # -------------------------
    usage_instruction = "continue_conversation"
    
    if "remember" in message or "recall" in message:
        usage_instruction = "retrieve_memory"
    elif "compare" in message or "difference" in message:
        usage_instruction = "compare_and_contrast"
    elif "summarize" in message or "summary" in message:
        usage_instruction = "summarize_context"
    elif "what did" in message or "what was" in message:
        usage_instruction = "recall_specific"
    elif "help me" in message or "assist" in message:
        usage_instruction = "provide_assistance"
    elif "plan" in message or "organize" in message:
        usage_instruction = "planning_support"

    return {
        "entity": entity,
        "topic": topic, 
        "usage_instruction": usage_instruction,
        "text_blocks": [user_message],
        "confidence_score": _calculate_confidence(entity, topic, user_message)
    }


def _calculate_confidence(entity: str, topic: str, message: str) -> float:
    """
    Calculate confidence score for extracted signals.
    Higher score = more confident in the extraction.
    """
    score = 0.0
    
    # Higher confidence if we found specific entities
    if entity != "general":
        score += 0.4
        
    # Higher confidence if we found specific topics  
    if topic != "general_chat":
        score += 0.4
        
    # Higher confidence for longer messages (more context)
    if len(message.split()) > 10:
        score += 0.2
        
    return min(score, 1.0)


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def extract_people_names(text: str) -> List[str]:
    """Extract potential people names from text."""
    # Simple heuristic: capitalized words that aren't common words
    common_words = {"The", "This", "That", "And", "But", "Or", "In", "On", "At", "To", "For"}
    
    potential_names = re.findall(r'\b[A-Z][a-z]+\b', text)
    return [name for name in potential_names if name not in common_words]


def extract_key_phrases(text: str) -> List[str]:
    """Extract key phrases that might be important for memory."""
    # Extract phrases in quotes
    quoted_phrases = re.findall(r'"([^"]*)"', text)
    
    # Extract phrases with common important patterns
    important_patterns = [
        r'project\s+\w+',
        r'meeting\s+with\s+\w+',
        r'deadline\s+\w+',
        r'budget\s+of\s+[\d,]+',
    ]
    
    key_phrases = quoted_phrases.copy()
    for pattern in important_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        key_phrases.extend(matches)
    
    return key_phrases
