import os
import httpx
import json
from typing import List
from app.models.product import ProductModel
from app.schemas.chat import ChatBotResponse
from langfuse import observe

class LLMService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_model = os.getenv("HF_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")

    @observe(as_type="generation")
    async def generate_rag_response(self, query: str, products: List[ProductModel]) -> ChatBotResponse:
        if not products:
            context = "No products found in database."
        else:
            context_items = []
            for p in products:
                desc = p.description or "No description available"
                context_items.append(f"- ID: {p.id}\n  Name: {p.name}\n  Description: {desc}\n  Price: ${p.price}\n  Stock: {p.stock}")
            context = "\n\n".join(context_items)

        system_prompt = (
            "You are an expert e-commerce customer support assistant.\n"
            "Your goal is to answer the user's question accurately using ONLY the retrieved products listed below.\n\n"
            "=== RETRIEVED PRODUCTS CONTEXT ===\n"
            f"{context}\n"
            "==================================\n\n"
            "STRICT RULES FOR YOUR ANSWER:\n"
            "1. ONLY base your answer on the retrieved products context above.\n"
            "2. If the context contains 'No products found' or no products are relevant to the query, respond with: 'I'm sorry, we do not carry any products matching that description.' and do not suggest anything else.\n"
            "3. DO NOT extrapolate, assume, or invent product details (like colors, sizes, or stock) not explicitly written in the context. Doing so is considered a hallucination and is strictly forbidden.\n"
            "4. Mention prices and availability if relevant to the query.\n"
            "5. Maintain a professional, concise, and helpful tone."
        )

        response_obj = None
        model_name = "Mock-LLM-v1"

        if self.groq_key and not self.groq_key.startswith("gsk_mock"):
            try:
                import groq
                import instructor
                
                g_client = groq.Groq(api_key=self.groq_key)
                instr_client = instructor.from_groq(g_client)
                
                response_obj = instr_client.chat.completions.create(
                    model=self.groq_model,
                    response_model=ChatBotResponse,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.2,
                    max_retries=2
                )
                model_name = self.groq_model
            except Exception as e:
                print(f"[LLMService] Groq Instructor request failed: {e}")

        if not response_obj and self.openai_key:
            try:
                import openai
                import instructor
                
                oai_client = openai.AsyncOpenAI(api_key=self.openai_key)
                instr_client = instructor.from_openai(oai_client)
                
                response_obj = await instr_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=ChatBotResponse,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.2,
                    max_retries=2
                )
                model_name = "gpt-4o-mini"
            except Exception as e:
                print(f"[LLMService] OpenAI Instructor request failed: {e}")

        if not response_obj and self.hf_token:
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
                            hf_text = res[0].get("generated_text", "").split("[/INST]")[-1].strip()
                            response_obj = ChatBotResponse(
                                response=hf_text,
                                recommended_product_ids=[p.id for p in products],
                                follow_up_questions=["Can you tell me more about these products?", "Are these items in stock?"]
                            )
                            model_name = self.hf_model
            except Exception as e:
                print(f"[LLMService] HuggingFace Chat request failed: {e}")

        if not response_obj:
            response_obj = self._generate_mock_rag_response(query, products)
            model_name = "Mock-LLM-v1"

        prompt_tokens = len(system_prompt + query) // 4
        completion_tokens = len(response_obj.response) // 4
        try:
            from opentelemetry import trace
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("langfuse.observation.model.name", model_name)
                current_span.set_attribute(
                    "langfuse.observation.usage_details",
                    json.dumps({
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens
                    })
                )
        except Exception:
            pass

        return response_obj

    def _generate_mock_rag_response(self, query: str, products: List[ProductModel]) -> ChatBotResponse:
        if not products:
            return ChatBotResponse(
                response="I'm sorry, we do not carry any products matching that description.",
                recommended_product_ids=[],
                follow_up_questions=["Do you have a different category?", "Can I search for another product?"]
            )

        recommended_ids = [p.id for p in products]
        
        q_lower = query.lower()
        if "camping" in q_lower or "sleeping" in q_lower or "warm" in q_lower:
            sleeping_bag = next((p for p in products if "sleeping" in p.name.lower()), None)
            if sleeping_bag:
                return ChatBotResponse(
                    response=f"Yes! We have the '{sleeping_bag.name}' in stock for ${sleeping_bag.price}. It is described as: {sleeping_bag.description}",
                    recommended_product_ids=[sleeping_bag.id],
                    follow_up_questions=["Is it waterproof?", "What are the dimensions?"]
                )
        elif "chef" in q_lower or "knife" in q_lower or "kitchen" in q_lower or "utensil" in q_lower:
            chef_knife = next((p for p in products if "knife" in p.name.lower()), None)
            if chef_knife:
                return ChatBotResponse(
                    response=f"We carry high-quality kitchen gear! You should check out the '{chef_knife.name}' (${chef_knife.price}). It features: {chef_knife.description}",
                    recommended_product_ids=[chef_knife.id],
                    follow_up_questions=["How long is the blade?", "Is it dishwasher safe?"]
                )

        product_list_str = ", ".join([f"'{p.name}' (${p.price})" for p in products])
        return ChatBotResponse(
            response=f"Based on our catalog, we recommend checking out the following matching products: {product_list_str}.",
            recommended_product_ids=recommended_ids,
            follow_up_questions=["What is the shipping cost?", "Are there discounts for bulk purchases?"]
        )

llm_service = LLMService()
