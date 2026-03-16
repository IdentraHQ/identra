import re
import time
import logging
from typing import Dict, List, Optional, Any
from collections import Counter

# Configure Logging
logger = logging.getLogger(__name__)

class UniversalSignalExtractor:
    """
    Extracts universal signals, intents, and entities from user messages
    to drive memory selection and context building.
    
    Robustness:
    - Loads NLP models lazily/safely to prevent module-import crashes.
    - Falls back to Regex if spaCy or its models are missing.
    """

    def __init__(self):
        # 1. Safe Initialization of NLP resources
        self.nlp = None
        self.has_spacy = False
        self._initialize_nlp()
        
        # 2. Compile Patterns
        self._compile_patterns()

    def _initialize_nlp(self):
        """
        Attempts to load spaCy and the English model safely.
        If this fails (missing lib or missing model), it logs a warning
        and the system continues in 'Regex Fallback' mode.
        """
        try:
            import spacy
            # Attempt to load the specific model
            # disable parser/textcat for speed (we only need NER)
            self.nlp = spacy.load("en_core_web_sm", disable=["parser", "textcat"])
            self.has_spacy = True
            logger.info("UniversalSignalExtractor: spaCy 'en_core_web_sm' loaded successfully.")
        except ImportError:
            logger.warning("UniversalSignalExtractor: spaCy library not found. Using Regex fallback.")
            self.has_spacy = False
        except Exception as e:
            # Catch OSError, IOError, or generic Exceptions if model is missing
            logger.warning(f"UniversalSignalExtractor: spaCy model load failed ({str(e)}). Using Regex fallback.")
            self.has_spacy = False

    def _compile_patterns(self):
        """Compile regex patterns and keyword weights for fast classification."""
        
        # --- 1. Classification Keywords & Weights ---
        self.TYPE_SIGNALS = {
            "TECHNICAL_HELP": {
                "debug": 2, "error": 2, "code": 1, "api": 2, "deploy": 2, "stack trace": 3,
                "function": 1, "variable": 1, "compile": 2, "architecture": 2, "latency": 2,
                "python": 1, "javascript": 1, "sql": 1, "bug": 2, "fix": 1
            },
            "WORK_PROJECT": {
                "sprint": 3, "jira": 3, "deadline": 2, "meeting": 1, "stakeholder": 2,
                "project": 1, "team": 1, "report": 1, "manager": 1, "roadmap": 2,
                "quarter": 1, "kpi": 2, "deliverable": 2, "status": 1
            },
            "CREATIVE": {
                "design": 2, "draft": 1, "color": 1, "logo": 2, "brainstorm": 2,
                "content": 1, "write": 1, "story": 1, "video": 1, "edit": 1,
                "palette": 2, "font": 1, "layout": 2, "inspiration": 1
            },
            "PERSONAL": {
                "feel": 1, "life": 1, "advice": 1, "decision": 1, "friend": 1,
                "relationship": 2, "personal": 1, "goal": 1, "struggle": 2, "habit": 1,
                "worry": 1, "happy": 1, "sad": 1, "weekend": 1
            },
            "GENERAL_QUERY": {
                "what is": 2, "who is": 2, "when": 1, "weather": 2, "news": 1,
                "search": 1, "find": 1, "price": 1, "location": 1
            }
        }

        self.THEME_SIGNALS = {
            "PROJECT_PLANNING": ["plan", "timeline", "schedule", "milestone", "resource"],
            "TROUBLESHOOTING": ["broken", "fail", "issue", "crash", "wrong", "help", "stuck"],
            "INFORMATION_SEEKING": ["tell me", "define", "explain", "history", "summary"],
            "BRAINSTORMING": ["idea", "think", "suggest", "option", "alternative", "concept"],
            "DECISION_MAKING": ["choose", "compare", "better", "pros and cons", "versus", "vs"],
            "LEARNING": ["learn", "tutorial", "guide", "understand", "teach"]
        }

        # --- 2. Intent Patterns (Regex for structural analysis) ---
        self.INTENT_PATTERNS = {
            "ACTIONABLE": re.compile(r"^(create|write|fix|debug|schedule|book|buy|send|generate|build)", re.IGNORECASE),
            "INFORMATIONAL": re.compile(r"^(what|who|when|where|why|how|explain|define|show me)", re.IGNORECASE),
            "ANALYTICAL": re.compile(r"(analyze|compare|evaluate|assess|review|difference between)", re.IGNORECASE),
            "CREATIVE": re.compile(r"(imagine|design|invent|story|poem|idea)", re.IGNORECASE),
        }

        # --- 3. Custom Entity Regex (Fallback & Technical Terms) ---
        self.TECH_ENTITY_REGEX = re.compile(r"\b([A-Z][a-zA-Z0-9]+|[a-z]+_[a-z]+|[A-Z]{2,}|[\w]+\.(py|js|ts|cpp|java|go|rs))\b")

    def extract_signals(self, user_message: str, history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Main entry point. Processes text and returns structured signal dictionary.
        """
        start_time = time.time()
        text_lower = user_message.lower()

        # 1. Classification
        conv_type = self._detect_conversation_type(text_lower)
        context_theme = self._detect_context_theme(text_lower, conv_type)
        intent = self._classify_intent(user_message, text_lower)

        # 2. Entity Extraction
        entities = self._extract_dynamic_entities(user_message)

        # 3. State & Memory Scope
        state = self._determine_state(entities, conv_type, history)
        memory_scope = self._determine_memory_scope(state, intent)

        # 4. Construct Output
        result = {
            "conversation_type": conv_type,
            "context_theme": context_theme,
            "intent_category": intent,
            "key_entities": entities,
            "conversation_state": state,
            "memory_scope": memory_scope,
            # Maintain compatibility with Context Pack builder
            "text_blocks": [user_message], 
            "extracted_at_ms": round((time.time() - start_time) * 1000, 2),
            "extraction_mode": "hybrid_spacy" if self.has_spacy else "regex_fallback"
        }

        return result

    def _detect_conversation_type(self, text: str) -> str:
        """Score text against weighted keywords to determine high-level type."""
        scores = Counter()
        
        for category, keywords in self.TYPE_SIGNALS.items():
            for word, weight in keywords.items():
                if word in text:
                    scores[category] += weight
        
        if not scores:
            return "GENERAL_QUERY"
        
        return scores.most_common(1)[0][0]

    def _detect_context_theme(self, text: str, conv_type: str) -> str:
        """Determine specific theme (Planning, Troubleshooting) based on context."""
        for theme, keywords in self.THEME_SIGNALS.items():
            if any(k in text for k in keywords):
                return theme
        
        defaults = {
            "TECHNICAL_HELP": "TROUBLESHOOTING",
            "WORK_PROJECT": "PROJECT_PLANNING",
            "CREATIVE": "BRAINSTORMING",
            "PERSONAL": "INFORMATION_SEEKING",
            "GENERAL_QUERY": "INFORMATION_SEEKING"
        }
        return defaults.get(conv_type, "GENERAL_DISCUSSION")

    def _classify_intent(self, original_text: str, text_lower: str) -> str:
        """Classify intent (Actionable vs Informational) using regex and heuristics."""
        for intent, pattern in self.INTENT_PATTERNS.items():
            if pattern.search(original_text):
                return intent
        
        if "?" in original_text:
            return "INFORMATIONAL"
        if len(text_lower.split()) < 4: 
            return "CONVERSATIONAL"
            
        return "CONVERSATIONAL"

    def _extract_dynamic_entities(self, text: str) -> List[str]:
        """
        Extract relevant entities using SpaCy (if available) + Regex for technical terms.
        """
        extracted = set()

        # A. SpaCy Extraction (Person, Org, GPE, Dates)
        if self.has_spacy and self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "WORK_OF_ART", "DATE"]:
                        extracted.add(ent.text)
            except Exception as e:
                # Fallback if runtime error occurs in spacy
                logger.error(f"NER extraction failed: {e}")

        # B. Regex Extraction (Tech terms like 'UserAuth', 'main_loop', 'pandas')
        tech_matches = self.TECH_ENTITY_REGEX.findall(text)
        for match in tech_matches:
            token = match[0] if isinstance(match, tuple) else match
            if len(token) > 3:
                extracted.add(token)

        # C. Keyword Extraction (from Type Signals)
        text_lower = text.lower()
        all_keywords = [k for cat in self.TYPE_SIGNALS.values() for k in cat.keys()]
        for kw in all_keywords:
            if kw in text_lower and len(kw) > 3:
                start = text_lower.find(kw)
                if start != -1:
                    extracted.add(text[start:start+len(kw)])

        return list(extracted)

    def _determine_state(self, current_entities: List[str], current_type: str, history: Optional[List[Dict]]) -> str:
        """Analyze conversation flow: New Topic, Continuation, Switch, or Deep Dive."""
        if not history:
            return "NEW_TOPIC"

        last_entry = history[-1] if history else {}
        
        last_type = last_entry.get("signals", {}).get("conversation_type", "")
        if last_type and last_type != current_type:
            return "CONTEXT_SWITCH"

        last_entities = last_entry.get("signals", {}).get("key_entities", [])
        
        curr_set = set(e.lower() for e in current_entities)
        last_set = set(e.lower() for e in last_entities)
        
        overlap = curr_set.intersection(last_set)
        
        if len(overlap) > 0:
            return "DEEP_DIVE"
        elif len(current_entities) > 0 and len(last_entities) > 0:
            return "CONTINUATION" 
        else:
            return "CONTINUATION"

    def _determine_memory_scope(self, state: str, intent: str) -> str:
        """Map state and intent to the required memory scope."""
        if state == "NEW_TOPIC":
            return "RECENT_SESSION"
        if state == "CONTEXT_SWITCH":
            return "LONG_TERM_PATTERN"
        if state == "DEEP_DIVE":
            if intent in ["ANALYTICAL", "ACTIONABLE"]:
                return "FULL_CONTEXT"
            return "RECENT_SESSION"
        if intent == "INFORMATIONAL":
            return "LONG_TERM_PATTERN"
        return "RECENT_SESSION"


# --- Example Usage (Integration Test) ---
if __name__ == "__main__":
    extractor = UniversalSignalExtractor()
    
    # Simulating a Work/Technical query
    msg1 = "We need to debug the AuthController in the Q3_Sprint project. The JWT token is invalid."
    print(f"Input: {msg1}")
    signals1 = extractor.extract_signals(msg1)
    print(f"Output: {signals1}\n")

    # Simulating a Context Switch to Creative
    msg2 = "Okay enough of that. Help me brainstorm a logo design for a coffee shop named 'JavaLife'."
    # Passing msg1 context conceptually (in real app, this is the history list)
    fake_history = [{"role": "user", "content": msg1, "signals": signals1}]
    
    print(f"Input: {msg2}")
    signals2 = extractor.extract_signals(msg2, history=fake_history)
    print(f"Output: {signals2}")