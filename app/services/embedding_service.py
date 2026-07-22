import os
from typing import List
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.hf_model = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.dimension = 384
        logger.info(f"[EmbeddingService] Loading SentenceTransformer model '{self.hf_model}'...")
        self.local_model = SentenceTransformer(self.hf_model)
        logger.info(f"[EmbeddingService] Successfully loaded local SentenceTransformer model '{self.hf_model}'")

    async def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension

        embedding = self.local_model.encode(text)
        return [float(x) for x in embedding]

embedding_service = EmbeddingService()
