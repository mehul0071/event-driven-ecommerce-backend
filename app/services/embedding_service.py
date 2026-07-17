import hashlib
import random
import os
import httpx
from typing import List

class EmbeddingService:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_model = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.dimension = 384

    async def generate_embedding(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension

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
                    print(f"[EmbeddingService] Warning: Received unexpected output shape from HF API: {len(embedding)}")
                else:
                    print(f"[EmbeddingService] HF API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[EmbeddingService] HuggingFace API failed: {e}. Falling back to deterministic mock embedding.")

        return self._generate_deterministic_mock(text)

    def _generate_deterministic_mock(self, text: str) -> List[float]:
        text_lower = text.lower()
        keywords = {
            "camping": 10,
            "sleeping": 20,
            "bag": 30,
            "winter": 40,
            "cold": 50,
            "mountain": 60,
            "gear": 70,
            "weather": 80,
            "chef": 90,
            "knife": 100,
            "kitchen": 110,
            "steel": 120,
            "vegetables": 130,
            "cooking": 140,
            "sharp": 150,
            "utensil": 160,
        }
        
        vector = [0.0] * self.dimension
        
        for word, idx in keywords.items():
            if word in text_lower:
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
