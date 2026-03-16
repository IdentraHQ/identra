import logging
import numpy as np
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_embedding")

# --- MISSING CLASSES ADDED HERE ---
class EmbeddingConfig(BaseModel):
    model_name: str = "all-MiniLM-L6-v2"
    device: str = "cpu"
    normalize_embeddings: bool = True

class EmbeddingResult(BaseModel):
    vector: List[float]
    dimension: int
    model_used: str

class EmbeddingService:
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initializes the local embedding model using the provided config.
        """
        self.config = config or EmbeddingConfig()
        logger.info(f"Loading Embedding Model: {self.config.model_name}...")
        
        try:
            self.model = SentenceTransformer(self.config.model_name, device=self.config.device)
            self.vector_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"✅ Embedding Model Loaded (Dim: {self.vector_dimension})")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise e

    def generate_embedding(self, text: str) -> List[float]:
        """
        Converts a single text string into a vector.
        """
        try:
            # Encode returns a numpy array, convert to list
            vector = self.model.encode(text, normalize_embeddings=self.config.normalize_embeddings)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def calculate_similarity(self, vector_a: List[float], vector_b: List[float]) -> float:
        """
        Calculates Cosine Similarity.
        """
        a = np.array(vector_a)
        b = np.array(vector_b)
        
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))