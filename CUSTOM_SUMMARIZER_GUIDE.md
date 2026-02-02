# Custom Summarizer Fine-Tuning Guide 🎨

Quick reference for how to adjust your custom summarizer to match your exact needs.

## Output Format Example

Your custom summarizer outputs this structured format:

```
[MEANING]
What is this memory about?

[FACTS]
Key information extracted from text

[CONSTRAINTS]
What actions are forbidden/allowed?

[ROLE]
What role should the assistant take?

[TIME]
created_at=2026-02-01T12:30:45.123456
```

---

## Common Fine-Tuning Scenarios

### Scenario 1: Extract More Specific Facts

**Current:** Extracts first 3 sentences
**Goal:** Extract key facts about prices, locations, features

**Edit `custom_summarizer.py`:**

```python
def _extract_facts(self, text: str, topic: str) -> str:
    """Extract key facts - ENHANCED VERSION"""
    facts = []
    text_lower = text.lower()
    
    # Extract specific patterns
    # Price extraction
    import re
    prices = re.findall(r'\$?\d+(?:\.\d+)?', text)
    if prices:
        facts.append(f"price_range: ${prices[0]}-${prices[-1] if len(prices) > 1 else prices[0]}")
    
    # Location extraction
    if "location" in text_lower or "located" in text_lower:
        sentences = text.split(".")
        for sent in sentences:
            if "location" in sent.lower() or "located" in sent.lower():
                facts.append(sent.strip()[:100])
                break
    
    # Feature extraction
    features = []
    feature_keywords = ["has", "includes", "features", "with"]
    for keyword in feature_keywords:
        if keyword in text_lower:
            sentences = text.split(".")
            for sent in sentences:
                if keyword in sent.lower():
                    features.append(sent.strip())
    
    if features:
        facts.append(f"features: {' | '.join(features[:3])}")
    
    return "\n".join(facts) if facts else "No specific facts found"
```

**Test it:**
```bash
python test_summarizer.py  # See new output format
```

---

### Scenario 2: Add Custom Constraints for Your Domain

**Current:** Generic forbidden/allowed actions
**Goal:** Hotel-specific constraints (pets, smoking, parking, etc.)

**Edit `custom_summarizer.py`:**

```python
def _extract_constraints(self, text: str, usage: str) -> str:
    """Extract domain-specific constraints - HOTEL VERSION"""
    text_lower = text.lower()
    
    constraints = {
        "pets": None,
        "smoking": None,
        "parking": None,
        "cancellation": None,
        "check_in": None,
        "breakfast": None,
    }
    
    # Detect constraints from text
    if any(word in text_lower for word in ["no pet", "pet-free", "no animals"]):
        constraints["pets"] = "forbidden"
    elif any(word in text_lower for word in ["pet friendly", "pets allowed", "allow pets"]):
        constraints["pets"] = "allowed"
    
    if any(word in text_lower for word in ["no smoking", "smoking-free"]):
        constraints["smoking"] = "forbidden"
    elif any(word in text_lower for word in ["smoking area", "smoking room"]):
        constraints["smoking"] = "allowed"
    
    if any(word in text_lower for word in ["free parking", "parking included"]):
        constraints["parking"] = "free"
    elif any(word in text_lower for word in ["paid parking", "parking fee"]):
        constraints["parking"] = "paid"
    
    if "free cancellation" in text_lower:
        constraints["cancellation"] = "free"
    elif "non-refundable" in text_lower:
        constraints["cancellation"] = "none"
    
    # Format output
    result = []
    for key, value in constraints.items():
        if value:
            result.append(f"{key}={value}")
    
    return "\n".join(result) if result else "No specific constraints"
```

**Test with hotel text:**
```python
text = [
    "Pet-friendly hotel with free parking",
    "Free cancellation up to 7 days before check-in",
    "Smoking-free rooms, outdoor smoking area available"
]
summary = summarize_text_blocks(text, topic="hotels", usage_instruction="book")
print(summary)
# Output should show: pets=allowed, parking=free, smoking=forbidden, cancellation=free
```

---

### Scenario 3: Improve Meaning Based on Topic

**Current:** Generic meaning message
**Goal:** Topic-specific summaries

**Edit `custom_summarizer.py`:**

```python
def _extract_meaning(self, text: str, topic: str, usage: str) -> str:
    """Extract meaning - TOPIC-AWARE VERSION"""
    
    # Topic-specific patterns
    topic_meanings = {
        "hotels": {
            "explore": "Hotel information for browsing and selection",
            "compare": "Comparison details between hotel options",
            "book": "Hotel booking requirements and policies",
        },
        "restaurants": {
            "explore": "Restaurant information and menu details",
            "compare": "Comparing cuisine, price, and reviews",
            "book": "Reservation requirements and timing",
        },
        "beaches": {
            "explore": "Beach information and attractions",
            "compare": "Comparing beaches by features and amenities",
            "book": "Access and parking information",
        }
    }
    
    # Get topic-specific meaning
    if topic in topic_meanings and usage in topic_meanings[topic]:
        return topic_meanings[topic][usage]
    
    # Fallback to generic
    return f"{usage.capitalize()} information about {topic}"
```

**Add more topics as needed:**
```python
topic_meanings["flights"] = {
    "explore": "Flight options and schedules",
    "compare": "Comparing airlines, prices, and timings",
    "book": "Booking requirements and payment methods",
}

topic_meanings["trains"] = {
    "explore": "Train routes and schedules",
    "compare": "Comparing train classes and prices",
    "book": "Ticket booking and cancellation policies",
}
```

---

### Scenario 4: Extract Role Based on Context

**Current:** Role based only on usage_instruction
**Goal:** More nuanced role assignment

**Edit `custom_summarizer.py`:**

```python
def _extract_role(self, usage_instruction: str, text: str = "") -> str:
    """Extract role - CONTEXT-AWARE VERSION"""
    
    # Start with usage instruction
    role_map = {
        "explore": "explorer_assistant",
        "compare": "comparison_assistant", 
        "book": "booking_assistant",
        "research": "research_assistant",
        "recommend": "recommendation_assistant",
    }
    
    role = role_map.get(usage_instruction, "general_assistant")
    
    # Enhance role based on context if text provided
    text_lower = text.lower() if text else ""
    
    if text_lower:
        if "luxury" in text_lower or "premium" in text_lower or "5-star" in text_lower:
            role = f"{role}_luxury"
        elif "budget" in text_lower or "affordable" in text_lower or "budget" in text_lower:
            role = f"{role}_budget"
        
        if "family" in text_lower:
            role = f"{role}_family"
        elif "solo" in text_lower or "single" in text_lower:
            role = f"{role}_solo"
    
    return f"assistant_role={role}"
```

**Test it:**
```python
# Should output: assistant_role=booking_assistant_luxury_family
summary = summarize_text_blocks(
    ["Luxury 5-star hotel perfect for families"],
    topic="hotels",
    usage_instruction="book"
)
```

---

### Scenario 5: Adjust Summary Lengths

**Current:** Max 200 chars, min 30 chars
**Goal:** Longer summaries with more detail

**Edit `custom_summarizer.py`:**

```python
class CustomSummarizer:
    def __init__(self):
        # More detailed summaries
        self.max_length = 500  # Increased from 200
        self.min_length = 50   # Increased from 30
        self.fact_limit = 150  # New: limit facts to 150 chars
        self.max_facts = 5     # New: max 5 facts extracted
```

Or make it configurable:

```python
class CustomSummarizer:
    def __init__(self, max_length: int = 200, min_length: int = 30):
        self.max_length = max_length
        self.min_length = min_length

# Use it:
_summarizer = CustomSummarizer(max_length=500, min_length=50)
```

---

## Testing Your Changes

### Quick Test Script

```python
# test_custom_adjustments.py
from summarizer.custom_summarizer import summarize_text_blocks

def test_your_adjustments():
    """Test specific scenario you're fine-tuning"""
    
    test_cases = [
        {
            "name": "Luxury hotel with pets",
            "text": [
                "5-star luxury hotel with pet-friendly rooms",
                "Parking included, free breakfast for guests",
                "Located near beaches and restaurants"
            ],
            "topic": "hotels",
            "usage": "book"
        },
        {
            "name": "Budget restaurant comparison",
            "text": [
                "Restaurant A: Indian cuisine, $10/plate",
                "Restaurant B: Italian, $15/plate", 
                "Both have outdoor seating"
            ],
            "topic": "restaurants",
            "usage": "compare"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*50}")
        print(f"Test: {test['name']}")
        print(f"{'='*50}")
        
        summary = summarize_text_blocks(
            text_blocks=test['text'],
            topic=test['topic'],
            usage_instruction=test['usage']
        )
        print(summary)
        
        # TODO: Check if output matches your expectations
        # If not, adjust extraction methods and re-run

if __name__ == "__main__":
    test_your_adjustments()
```

Run it:
```bash
python test_custom_adjustments.py
```

---

## Iteration Loop

1. **Run test**: `python test_summarizer.py`
2. **Check output**: Does [MEANING], [FACTS], [CONSTRAINTS] look good?
3. **If NO**: Edit the extraction method
4. **If YES**: Move to next test case or use in main app

**Repeat until happy!** ✅

---

## Pro Tips

### Tip 1: Add Debug Output
```python
def _extract_facts(self, text: str, topic: str) -> str:
    print(f"DEBUG: Extracting facts from: {text[:50]}...")
    facts = [...]
    print(f"DEBUG: Found {len(facts)} facts")
    return "\n".join(facts)
```

### Tip 2: Create Test Fixtures
```python
HOTEL_TEXTS = {
    "luxury": ["5-star hotel", "premium amenities", "spa and wellness"],
    "budget": ["affordable rates", "$50/night", "basic rooms"],
    "family": ["family rooms", "kid-friendly", "playground"]
}

# Test all fixtures
for category, texts in HOTEL_TEXTS.items():
    summary = summarize_text_blocks(texts, topic="hotels")
    print(f"{category}: {summary[:50]}...")
```

### Tip 3: Version Your Summarizer
```python
# Keep old versions, create new ones
class CustomSummarizerV1:
    pass

class CustomSummarizerV2:
    # Improved version
    pass

# Switch between versions in main app
from summarizer.custom_summarizer import CustomSummarizerV2 as CustomSummarizer
```

---

## When to Replace with ML

You might want to add ML later if:
- Pattern matching becomes too complex
- You need to handle too many edge cases
- You want to learn from user feedback
- Domain is very diverse

But **start with this!** It's fast, clear, and works great for MVP. 🚀
