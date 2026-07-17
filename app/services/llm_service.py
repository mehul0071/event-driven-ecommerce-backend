import os
import httpx
from typing import List
from app.models.product import ProductModel

class LLMService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_model = os.getenv("HF_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

    async def generate_rag_response(self, query: str, products: List[ProductModel]) -> str:
        if not products:
            context = "No products found in database."
        else:
            context_items = []
            for p in products:
                desc = p.description or "No description available"
                context_items.append(f"- ID: {p.id}\n  Name: {p.name}\n  Description: {desc}\n  Price: ${p.price}\n  Stock: {p.stock}")
            context = "\n\n".join(context_items)

        system_prompt = (
            "You are a helpful e-commerce support assistant. Below are products matching the user's inquiry:\n"
            f"{context}\n\n"
            "Use the product list above to answer the user's question accurately. "
            "If no relevant products are present or context says 'No products found', tell the user we don't carry matching products. "
            "Do not make up or hallucinate product details. Be concise and professional."
        )

        if self.openai_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": query}
                            ],
                            "temperature": 0.2
                        },
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[LLMService] OpenAI request failed: {e}")

        if self.hf_token:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://api-inference.huggingface.co/models/{self.hf_model}",
                        headers={"Authorization": f"Bearer {self.hf_token}"},
                        json={
                            "inputs": f"<s>[INST] {system_prompt}\n\nUser Question: {query} [/INST] </s>",
                            "parameters": {"max_new_tokens": 250, "temperature": 0.2}
                        },
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        res = response.json()
                        if isinstance(res, list) and len(res) > 0:
                            return res[0].get("generated_text", "").split("[/INST]")[-1].strip()
            except Exception as e:
                print(f"[LLMService] HuggingFace Chat request failed: {e}")

        return self._generate_mock_rag_response(query, products)

    def _generate_mock_rag_response(self, query: str, products: List[ProductModel]) -> str:
        if not products:
            return "I'm sorry, we don't have any products matching your description in our inventory."

        product_list_str = ", ".join([f"'{p.name}' (${p.price})" for p in products])
        
        q_lower = query.lower()
        if "camping" in q_lower or "sleeping" in q_lower or "warm" in q_lower:
            sleeping_bag = next((p for p in products if "sleeping" in p.name.lower()), None)
            if sleeping_bag:
                return (
                    f"Yes! We have the '{sleeping_bag.name}' in stock for ${sleeping_bag.price}. "
                    f"It is described as: {sleeping_bag.description}"
                )
        elif "chef" in q_lower or "knife" in q_lower or "kitchen" in q_lower or "utensil" in q_lower:
            chef_knife = next((p for p in products if "knife" in p.name.lower()), None)
            if chef_knife:
                return (
                    f"We carry high-quality kitchen gear! You should check out the '{chef_knife.name}' (${chef_knife.price}). "
                    f"It features: {chef_knife.description}"
                )

        return f"Based on our catalog, we recommend checking out the following matching products: {product_list_str}."

llm_service = LLMService()
