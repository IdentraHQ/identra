# Brain Service Implementation Checklist ✅

Your personalized step-by-step checklist adapted from your existing code.

---

## Phase 0: Prerequisites (Already Done! ✅)

- [x] Python venv created (`.venv`)
- [x] Basic dependencies installed (fastapi)
- [x] You have analyzed your context-package-engine
- [x] You have the adapted plan (SAILESH_MVP_ADAPTED.md)

---

## Phase 1: Port Your Code (Day 1 - ~4 hours)

### Step 1.1: Create Directory Structure (15 min)
```bash
cd /home/srm/Projects/identra/apps/brain-service

# Create directories
mkdir -p engine summarizer tests

# Create __init__.py files
touch engine/__init__.py
touch summarizer/__init__.py
touch tests/__init__.py
```

Verify structure:
```bash
ls -la
# Should show: engine/, summarizer/, tests/, main.py, requirements.txt
```

- [ ] Directory structure created
- [ ] All __init__.py files exist

---

### Step 1.2: Create Custom Summarizer (45 min)

**File: `summarizer/custom_summarizer.py`**

Copy the custom summarizer code from SAILESH_MVP_ADAPTED.md Phase 1 section.

```bash
# Verify it exists and has no syntax errors
python -c "from summarizer.custom_summarizer import summarize_text_blocks; print('✅ Imports OK')"
```

- [ ] `summarizer/custom_summarizer.py` created
- [ ] No import errors
- [ ] `summarize_text_blocks()` function works

---

### Step 1.3: Test Custom Summarizer (20 min)

**File: `test_summarizer.py`** (in apps/brain-service root)

Copy test code from SAILESH_MVP_ADAPTED.md Phase 3 section.

```bash
# Run tests
python test_summarizer.py

# Check output for [MEANING], [FACTS], [CONSTRAINTS], [ROLE]
```

**Acceptance Criteria:**
- Output has all 4 sections
- Format is structured and readable
- No errors during summarization

- [ ] Test file created
- [ ] Test runs without errors
- [ ] Output format looks good
- [ ] Ready to fine-tune (if needed)

---

### Step 1.4: Port Engine Modules (1.5 hours)

Copy these EXACTLY from your context-package-engine:

**File: `engine/extractor.py`**
- Source: `context-package-engine/Engine/extractor.py`
- Changes: NONE (copy-paste)

```bash
python -c "from engine.extractor import extract_signals; print('✅ extractor imports OK')"
```

**File: `engine/memory_selector.py`**
- Source: `context-package-engine/Engine/memory_selector.py`
- Changes: 
  - Make `select_memory()` async (add `async def`)
  - Change parameter: `memory_store` → `memory_client`
  - Change call: `memory_store.get_by_entity()` → `await memory_client.get_by_entity()`

```bash
python -c "from engine.memory_selector import detect_generic_query; print('✅ memory_selector imports OK')"
```

**File: `engine/context_pack.py`**
- Source: `context-package-engine/Engine/context_pack.py`
- Changes: Update import at top:
  ```python
  from summarizer.custom_summarizer import summarize_text_blocks
  # Remove the FLAN-T5 import
  ```

```bash
python -c "from engine.context_pack import build_context_pack; print('✅ context_pack imports OK')"
```

- [ ] `engine/extractor.py` copied (no changes)
- [ ] `engine/memory_selector.py` copied (make async)
- [ ] `engine/context_pack.py` copied (update summarizer import)
- [ ] All imports work without errors

---

### Step 1.5: Create gRPC Memory Client Adapter (1 hour)

**File: `engine/memory_client.py`** (NEW)

Copy code from SAILESH_MVP_ADAPTED.md Phase 1.3 section.

```bash
python -c "from engine.memory_client import MemoryClient; print('✅ memory_client imports OK')"
```

- [ ] `engine/memory_client.py` created with gRPC adapter
- [ ] Has `connect()`, `get_by_entity()`, `store_memory()`, `close()` methods
- [ ] No import errors

---

### Step 1.6: Create Main FastAPI App (45 min)

**File: `main.py`**

Copy code from SAILESH_MVP_ADAPTED.md Phase 1.1 section.

Key changes from your original API/App.py:
1. Use `MemoryClient` instead of `MemoryStore`
2. Make functions `async`
3. Add `@app.on_event("startup")` and `@app.on_event("shutdown")`
4. Import from your modules: `engine.extractor`, `engine.memory_selector`, etc.

```bash
# Check for syntax errors
python -m py_compile main.py
echo "✅ main.py syntax OK"
```

- [ ] `main.py` created
- [ ] All imports resolve
- [ ] Syntax is correct
- [ ] Has `/health`, `/rag/orchestrate`, `/memory/*` endpoints

---

## Phase 2: Update Dependencies (30 min)

### Step 2.1: Update requirements.txt

**File: `requirements.txt`**

Replace entire contents with:

```txt
# Core FastAPI
fastapi==0.128.0
uvicorn[standard]==0.30.0
pydantic==2.12.5
python-dotenv==1.0.0

# gRPC for gateway communication
grpcio==1.64.1
grpcio-tools==1.64.1
protobuf==5.27.0

# Structured logging
structlog==24.1.0
```

- [ ] `requirements.txt` updated (NO transformers/torch)

### Step 2.2: Install Dependencies

```bash
cd /home/srm/Projects/identra/apps/brain-service

# Activate venv
source .venv/bin/activate

# Install
pip install -r requirements.txt

# Verify
pip list | grep fastapi
```

- [ ] Dependencies installed
- [ ] FastAPI, uvicorn, grpcio present
- [ ] NO torch or transformers (you don't need them!)

---

## Phase 3: Test Your Port (1 hour)

### Step 3.1: Test Individual Components

```bash
# Test custom summarizer
python test_summarizer.py
```

Check:
- [x] Summarizer works
- [x] Output format correct

```bash
# Test extractor
python -c "
from engine.extractor import extract_signals
result = extract_signals('I want to book a hotel in Bangalore')
print('Entity:', result['entity'])
print('Topic:', result['topic'])
print('Usage:', result['usage_instruction'])
"
```

Check:
- [x] Entity detection works (should be "Bangalore")
- [x] Topic detection works (should be "hotels")
- [x] Usage detection works (should be "book")

```bash
# Test memory selector
python -c "
from engine.memory_selector import detect_generic_query, detect_explicit_recall
print('Generic?', detect_generic_query('Tell me about hotels'))
print('Recall?', detect_explicit_recall('Remember when we visited?'))
"
```

Check:
- [x] Detection functions work

```bash
# Test context pack builder
python -c "
from engine.context_pack import build_context_pack
pack = build_context_pack(
    topic='hotels',
    text_blocks=['Great 5-star hotel'],
    usage_instruction='explore',
    entity='Bangalore'
)
print('Context Pack:', pack)
"
```

Check:
- [x] Returns dict with expected keys
- [x] Summary is generated

- [ ] Summarizer test passes
- [ ] Extractor works correctly
- [ ] Memory selector works
- [ ] Context pack builder works

### Step 3.2: Start Brain Service

```bash
# Terminal 1: Start the service
cd /home/srm/Projects/identra/apps/brain-service
source .venv/bin/activate
python main.py

# Should see:
# 🧠 Brain Service starting...
# ✅ Connected to gRPC gateway (or connection error - OK for now)
# Uvicorn running on http://0.0.0.0:8000
```

- [ ] Service starts without errors
- [ ] Logs show startup messages
- [ ] Listening on port 8000

### Step 3.3: Test API Endpoints

```bash
# Terminal 2: Test endpoints
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"brain"}

curl http://localhost:8000/ready
# Expected: {"ready":false,"gateway":"disconnected"} (OK - gateway not running yet)

# Test RAG orchestration
curl -X POST http://localhost:8000/rag/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"user_message":"I want to book a hotel in Bangalore"}'
# Expected: JSON with context_pack, selected_memories, enhanced_prompt
```

- [ ] `/health` endpoint works
- [ ] `/ready` endpoint works
- [ ] `/rag/orchestrate` endpoint works

### Step 3.4: Visit API Documentation

```
Open browser: http://localhost:8000/docs
```

You should see:
- All endpoints listed
- Request/response schemas
- "Try it out" button for each endpoint

- [ ] Swagger docs load
- [ ] All endpoints visible
- [ ] Can test endpoints in UI

---

## Phase 4: Fine-Tune Custom Summarizer (Optional - 30 min)

If basic summarizer output doesn't match your needs:

1. Read `CUSTOM_SUMMARIZER_GUIDE.md`
2. Edit extraction methods in `summarizer/custom_summarizer.py`
3. Re-run `test_summarizer.py`
4. Verify output matches your expectations
5. Update `main.py` if needed

- [ ] Reviewed custom summarizer output
- [ ] Made desired adjustments (if any)
- [ ] Tests pass with adjusted output

---

## Phase 5: Integration with Identra (Days 2-3)

### Step 5.1: Run Full Stack Test

```bash
# Terminal 1: Start database
just db-up

# Terminal 2: Start gateway (once DB is ready)
just dev-gateway

# Terminal 3: Start brain service
cd apps/brain-service && python main.py

# Terminal 4: Run integration test
python test_integration.py
```

- [ ] Database running
- [ ] Gateway connected
- [ ] Brain service connected to gateway
- [ ] Memory operations work end-to-end

### Step 5.2: Test with Desktop App (Optional)

```bash
# Terminal 5: Start desktop
just dev-desktop

# Send messages through chat interface
# Messages should flow: Desktop → Brain Service → Gateway → Database
```

- [ ] Chat interface sends messages to brain service
- [ ] Responses come back with enhanced context
- [ ] No errors in any service logs

---

## Phase 6: Production Polish (Optional)

### Step 6.1: Add Configuration

Create `config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gateway_address: str = "localhost:50051"
    brain_port: int = 8000
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

Update `main.py` to use it:
```python
from config import settings
app = FastAPI(...)
```

- [ ] Configuration in separate file
- [ ] Loadable from environment
- [ ] Used in main.py

### Step 6.2: Add Environment File

Create `.env.example`:
```bash
GATEWAY_ADDRESS=localhost:50051
BRAIN_PORT=8000
LOG_LEVEL=INFO
```

Copy to `.env`:
```bash
cp .env.example .env
```

- [ ] `.env.example` created
- [ ] `.env` file present (never commit)

### Step 6.3: Add Structured Logging

Update imports in `main.py`:
```python
import structlog
logger = structlog.get_logger()
logger.info("event", key="value")  # Structured logs
```

- [ ] Structured logging added
- [ ] Logs include context information

### Step 6.4: Create Docker Image

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

Build and test:
```bash
docker build -t identra-brain:latest .
docker run -p 8000:8000 identra-brain:latest
```

- [ ] Dockerfile created
- [ ] Image builds successfully
- [ ] Container runs and serves requests

---

## ✅ Final Verification

When you're done, verify everything works:

```bash
# 1. Unit tests
python test_summarizer.py

# 2. Component tests  
python -c "
from engine.extractor import extract_signals
from engine.memory_selector import select_memory
from engine.context_pack import build_context_pack
print('✅ All modules import successfully')
"

# 3. App startup
python main.py &
sleep 2
curl http://localhost:8000/health
pkill -f "python main.py"

# 4. Full stack (if available)
# just dev-gateway &
# python main.py &
# python test_integration.py
# pkill -f "python main.py"
# just db-down
```

- [ ] All unit tests pass
- [ ] All modules import without errors
- [ ] App starts and serves requests
- [ ] Endpoints respond correctly

---

## 🎉 You're Done!

Your Brain Service is ready! Next steps:

1. **Integration**: Connect to full Identra stack
2. **Testing**: Run with real chat interface
3. **Monitoring**: Add metrics and logging
4. **Deployment**: Deploy to production

---

## Quick Command Reference

```bash
# Setup
cd apps/brain-service
source .venv/bin/activate
pip install -r requirements.txt

# Test components
python test_summarizer.py

# Run service
python main.py

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Clean up
pkill -f "python main.py"
```

---

**Total time: ~1 day including integration** 🚀

You've got this, Sailesh! 💪
