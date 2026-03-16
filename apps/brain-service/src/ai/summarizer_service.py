import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("summarizer_service")

# --- Pydantic Data Models (The API Contract) ---

class SummarizationOptions(BaseModel):
    model: str = Field("llama3.1", description="Target model (llama3.1, mistral, etc)")
    temperature: float = Field(0.0, description="0.0 for precision, 0.7 for creativity")
    max_words: Optional[int] = Field(None, description="Approximate target length")
    format: str = Field("bullet_points", description="bullet_points, paragraph, or structured_report")
    privacy_mode: bool = Field(True, description="If True, sensitive content is not logged")
    technical_accuracy: bool = Field(True, description="Enforces strict number/fact preservation")

class SummarizationRequest(BaseModel):
    text: str = Field(..., description="The full input text to summarize")
    options: SummarizationOptions = Field(default_factory=SummarizationOptions)

class SummarizationMetrics(BaseModel):
    processing_time_ms: float
    input_token_count: int
    chunk_count: int
    model_used: str

class SummarizationResponse(BaseModel):
    summary: str
    metrics: SummarizationMetrics
    warnings: List[str] = []

# --- The Core Service Class ---

class SummarizerService:
    def __init__(self):
        # We can perform warm-up or connection checks here
        pass

    async def summarize(self, request: SummarizationRequest) -> SummarizationResponse:
        """
        Main entry point. Handles logic for short vs. long documents automatically.
        """
        start_time = time.time()
        text = request.text
        options = request.options
        warnings = []
        
        # 1. Input Validation & Pre-processing
        if not text.strip():
            raise ValueError("Input text cannot be empty.")

        # Estimate tokens (rough heuristic: 1 token ~= 4 chars)
        approx_tokens = len(text) / 4
        
        # 2. Strategy Selection: Single Shot vs. Chunking
        # Llama 3.1 has 8k context, but we play safe at 6k to leave room for response
        CONTEXT_LIMIT = 6000 
        
        try:
            if approx_tokens < CONTEXT_LIMIT:
                final_summary = await self._generate_single_shot(text, options)
                chunk_count = 1
            else:
                logger.info(f"Document too large ({int(approx_tokens)} tokens). Engaging chunking strategy.")
                final_summary, chunk_count = await self._generate_map_reduce(text, options)

        except Exception as e:
            # Fallback Logic: Try a smaller/faster model or return error
            logger.error(f"Summarization failed: {str(e)}")
            if options.model != "mistral":
                warnings.append(f"Primary model {options.model} failed. Attempting fallback to mistral.")
                options.model = "mistral"
                try:
                    final_summary = await self._generate_single_shot(text, options)
                    chunk_count = 1
                except Exception as fallback_error:
                    return self._create_error_response(str(fallback_error))
            else:
                 return self._create_error_response(str(e))

        # 3. Final Metrics Calculation
        processing_time = (time.time() - start_time) * 1000
        
        if not options.privacy_mode:
            logger.info(f"Summarized {len(text)} chars in {processing_time:.2f}ms")

        return SummarizationResponse(
            summary=final_summary,
            metrics=SummarizationMetrics(
                processing_time_ms=processing_time,
                input_token_count=int(approx_tokens),
                chunk_count=chunk_count,
                model_used=options.model
            ),
            warnings=warnings
        )

    # --- Internal Logic Methods ---

    async def _generate_single_shot(self, text: str, options: SummarizationOptions) -> str:
        """Handles text that fits within the context window."""
        system_prompt = self._build_system_prompt(options)
        
        user_prompt = f"Summarize the following text in {options.format} format:\n\n{text}"
        
        response = await self._safe_ollama_call(
            model=options.model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options=options
        )
        return response['message']['content']

    async def _generate_map_reduce(self, text: str, options: SummarizationOptions) -> (str, int):
        """
        Splits text, summarizes chunks in parallel, then summarizes the summaries.
        """
        chunks = self._intelligent_chunking(text)
        
        # Step 1: Map (Summarize each chunk)
        # We run these in parallel using asyncio.gather for speed
        tasks = [
            self._generate_single_shot(chunk, options) 
            for chunk in chunks
        ]
        chunk_summaries = await asyncio.gather(*tasks)
        
        # Step 2: Reduce (Combine summaries)
        combined_text = "\n\n".join(chunk_summaries)
        final_system_prompt = (
            "You are combining multiple partial summaries into one coherent report. "
            "Merge the following points, remove duplicates, and ensure logical flow."
        )
        
        final_response = await self._safe_ollama_call(
            model=options.model,
            messages=[
                {'role': 'system', 'content': final_system_prompt},
                {'role': 'user', 'content': f"Combined summaries:\n{combined_text}"}
            ],
            options=options
        )
        
        return final_response['message']['content'], len(chunks)

    def _intelligent_chunking(self, text: str, chunk_size: int = 12000, overlap: int = 500) -> List[str]:
        """
        Splits text by paragraphs to preserve meaning, staying under character limit.
        chunk_size 12000 chars is roughly 3000 tokens.
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            
            # If we are not at the end, find the last newline to break cleanly
            if end < text_len:
                # Look for last paragraph break
                last_break = text.rfind('\n\n', start, end)
                if last_break == -1:
                    last_break = text.rfind('\n', start, end)
                if last_break == -1:
                    last_break = text.rfind('. ', start, end)
                
                # If found a break point, use it; otherwise hard cut
                if last_break != -1 and last_break > start:
                    end = last_break + 1  # Include the punctuation

            chunks.append(text[start:end])
            start = end - overlap # Overlap to preserve context between chunks
        
        return chunks

    async def _safe_ollama_call(self, model: str, messages: List[dict], options: SummarizationOptions) -> dict:
        """
        Wrapper for Ollama API to handle timeouts and errors.
        """
        ollama_options = {
            'temperature': options.temperature,
            'num_ctx': 8192 if model == "llama3.1" else 4096,
        }
        
        # We run this in a thread executor because ollama.chat is synchronous (blocking)
        # unless we use the AsyncClient. Here we wrap the standard client for simplicity/stability.
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama is not installed. Install it or use a cloud provider.")

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, 
                lambda: ollama.chat(model=model, messages=messages, options=ollama_options)
            )
        except Exception as e:
            logger.error(f"Ollama API Error: {e}")
            raise e

    def _build_system_prompt(self, options: SummarizationOptions) -> str:
        prompt = "You are a professional analyst summarizer."
        
        if options.technical_accuracy:
            prompt += " STRICTLY PRESERVE all financial figures, dates, IDs, and technical terms. Do not hallucinate numbers."
        
        if options.format == "bullet_points":
            prompt += " Output the response as a concise list of bullet points."
        elif options.format == "structured_report":
            prompt += " Output with Markdown headers: ## Overview, ## Key Metrics, ## Action Items."
            
        return prompt

    def _create_error_response(self, error_msg: str) -> SummarizationResponse:
        return SummarizationResponse(
            summary="Could not generate summary due to an internal error.",
            metrics=SummarizationMetrics(
                processing_time_ms=0, input_token_count=0, chunk_count=0, model_used="error"
            ),
            warnings=[error_msg]
        )