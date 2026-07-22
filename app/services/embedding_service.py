import hashlib
import random
import os
import httpx
from typing import List
import logging
logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_model = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.dimension = 384
        self.local_model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(self.hf_model)
            logger.info(f"[EmbeddingService] Successfully loaded local SentenceTransformer model '{self.hf_model}'")
        except Exception as e:
            logger.info(f"[EmbeddingService] Warning: Failed to load local SentenceTransformer: {e}. Will fall back to HF API / mock.")

    async def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension

        if self.local_model:
            try:
                embedding = self.local_model.encode(text)
                return [float(x) for x in embedding]
            except Exception as e:
                logger.info(f"[EmbeddingService] Local encoding failed: {e}. Trying API fallback...")

        try:
            headers = {}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.hf_model}"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    api_url,
                    json={"inputs": text, "options": {"wait_for_model": True}},
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    embedding = response.json()
                    if isinstance(embedding, list):
                        if len(embedding) > 0 and isinstance(embedding[0], list):
                            embedding = embedding[0]
                        if len(embedding) == self.dimension:
                            return [float(x) for x in embedding]
                    logger.info(f"[EmbeddingService] Warning: Received unexpected output shape from HF API: {len(embedding)}")
                else:
                    logger.info(f"[EmbeddingService] HF API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logger.info(f"[EmbeddingService] HuggingFace API failed: {e}. Falling back to deterministic mock embedding.")

        return self._generate_deterministic_mock(text)

    def _generate_deterministic_mock(self, text: str) -> List[float]:
        text_lower = text.lower()
        keywords = {
            "camping": 10,
            "sleeping": 10,
            "bag": 10,
            "winter": 10,
            "cold": 10,
            "mountain": 10,
            "gear": 10,
            "weather": 10,
            "stove": 10,
            "backpack": 10,
            "tent": 10,
            
            "chef": 90,
            "knife": 90,
            "kitchen": 90,
            "steel": 90,
            "vegetables": 90,
            "cooking": 90,
            "sharp": 90,
            "utensil": 90,
            "circulator": 90,
            "skillet": 90,

            "dumbbell": 200,
            "fitness": 200,
            "yoga": 200,
            "mat": 200,

            "keyboard": 240,
            "chair": 240,
            "headphones": 240,
            "monitor": 240,

            "espresso": 280,
            "coffee": 280,
        }
        
        vector = [0.0] * self.dimension
        
        for word, idx in keywords.items():
            if word in text_lower or text_lower in word or (len(text_lower) >= 4 and word.startswith(text_lower[:4])):
                vector[idx] = 10.0 
                
        hash_object = hashlib.sha256(text.encode('utf-8'))
        hex_dig = hash_object.hexdigest()
        rng = random.Random(hex_dig)
        
        for i in range(self.dimension):
            if vector[i] == 0.0:
                vector[i] = rng.uniform(-0.1, 0.1)
                
        magnitude = sum(x**2 for x in vector)**0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]
            
        return vector

embedding_service = EmbeddingService()
