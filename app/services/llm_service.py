import os
import httpx
import json
import torch
import re
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from typing import List, Optional
from app.models.product import ProductModel
from app.schemas.chat import ChatBotResponse
from app.schemas.review import ReviewAnalysis, ReviewsConsensus
from langfuse import observe
import groq
import instructor
import openai
import logging
logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.hf_model = os.getenv("HF_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")
        self.adapter_path = "./fine_tuned_parser"
        self.base_model_id = "meta-llama/Meta-Llama-3-8B"
        self._model = None
        self._tokenizer = None
        self._model_loaded = False

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
                logger.info(f"[LLMService] Groq Instructor request failed: {e}")

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
                logger.info(f"[LLMService] OpenAI Instructor request failed: {e}")

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
                logger.info(f"[LLMService] HuggingFace Chat request failed: {e}")

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

    def _load_local_peft_model(self) -> bool:
        if self._model_loaded:
            return True
        
        hf_adapter_repo = os.getenv("HF_ADAPTER_REPO")
        adapter_to_load = hf_adapter_repo if hf_adapter_repo else self.adapter_path
        
        if not hf_adapter_repo and not os.path.exists(self.adapter_path):
            logger.info(f"[LLMService] Local adapter path {self.adapter_path} not found and HF_ADAPTER_REPO not set. Fallback to API/mock parser.")
            return False
        
        try:
            logger.info(f"[LLMService] Loading fine-tuned parser from {adapter_to_load}...")
            device_map = "auto" if torch.cuda.is_available() else "cpu"
            torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            self._tokenizer = AutoTokenizer.from_pretrained(self.base_model_id)
            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_id,
                torch_dtype=torch_dtype,
                device_map=device_map
            )
            self._model = PeftModel.from_pretrained(base_model, adapter_to_load)
            self._model.eval()
            self._model_loaded = True
            logger.info("[LLMService] Fine-tuned parser model loaded successfully.")
            return True
        except Exception as e:
            logger.info(f"[LLMService] Failed to load PEFT model: {e}")
            return False

    async def parse_product_description(self, description: str) -> dict:
        instruction = "Extract structured product attributes from the unstructured merchant description."
        prompt = f"System: {instruction}\nUser: {description}\nAssistant: "
        
        if self._load_local_peft_model():
            try:
                import torch
                inputs = self._tokenizer(prompt, return_tensors="pt")
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = self._model.generate(
                        **inputs,
                        max_new_tokens=150,
                        temperature=0.1,
                        do_sample=False
                    )
                
                generated_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
                response_part = generated_text[len(prompt):].strip()
                parsed_json = json.loads(response_part)
                return parsed_json
            except Exception as e:
                logger.info(f"[LLMService] Local PEFT inference failed: {e}. Falling back...")

        if self.groq_key and not self.groq_key.startswith("gsk_mock"):
            try:
                g_client = groq.Groq(api_key=self.groq_key)
                instr_client = instructor.from_groq(g_client)
                
                response_obj = instr_client.chat.completions.create(
                    model=self.groq_model,
                    response_model=ProductAttributes,
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": description}
                    ],
                    temperature=0.1,
                )
                return response_obj.model_dump()
            except Exception as e:
                logger.info(f"[LLMService] Groq API fallback for parser failed: {e}")

        if self.openai_key:
            try:
                oai_client = openai.AsyncOpenAI(api_key=self.openai_key)
                instr_client = instructor.from_openai(oai_client)
                
                response_obj = await instr_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=ProductAttributes,
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": description}
                    ],
                    temperature=0.1,
                )
                return response_obj.model_dump()
            except Exception as e:
                logger.info(f"[LLMService] OpenAI API fallback for parser failed: {e}")

        return self._fallback_rule_based_parser(description)

    def _fallback_rule_based_parser(self, description: str) -> dict:
        desc_lower = description.lower()
        
        price = 0.0
        price_match = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', description)
        if price_match:
            price = float(price_match.group(1))
            
        stock = 0
        stock_match = re.search(r'([0-9]+)\s*(?:left in stock|available|units|items|left)', desc_lower)
        if stock_match:
            stock = int(stock_match.group(1))
            
        color = None
        for c in ["red", "blue", "green", "yellow", "black", "white", "orange", "gray"]:
            if c in desc_lower:
                color = c
                break
                
        size = None
        size_match = re.search(r'([0-9]+-inch|small|medium|large|standard|compact)', desc_lower)
        if size_match:
            size = size_match.group(1)
            
        category = "general"
        for cat, keywords in {
            "outdoors": ["backpack", "stove", "sleeping bag", "camping", "tent"],
            "fitness": ["dumbbell", "weights", "fitness", "tracker"],
            "kitchen": ["knife", "skillet", "chef", "espresso"],
            "office": ["keyboard", "headphones", "monitor", "noise cancelling"]
        }.items():
            if any(k in desc_lower for k in keywords):
                category = cat
                break
                
        name = "unknown product"
        for kw in ["backpack", "camping stove", "dumbbell set", "mechanical keyboard", 
                   "noise cancelling headphones", "espresso machine", "gaming monitor", 
                   "chef knife", "cast iron skillet", "sleeping bag"]:
            if kw in desc_lower:
                name = kw
                break
                
        return {
            "name": name,
            "category": category,
            "color": color,
            "size": size,
            "price": price,
            "stock": stock
        }

    @observe(as_type="generation")
    async def analyze_review_sentiment_and_tags(self, comment: str) -> dict:
        instruction = "Classify the sentiment and extract key descriptive aspects (tags) from the user's product review."

        response_obj = None

        if self.groq_key and not self.groq_key.startswith("gsk_mock"):
            try:
                
                g_client = groq.Groq(api_key=self.groq_key)
                instr_client = instructor.from_groq(g_client)
                
                response_obj = instr_client.chat.completions.create(
                    model=self.groq_model,
                    response_model=ReviewAnalysis,
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": comment}
                    ],
                    temperature=0.1
                )
            except Exception as e:
                logger.info(f"[LLMService] Groq sentiment analysis failed: {e}")

        if not response_obj and self.openai_key:
            try:
                oai_client = openai.AsyncOpenAI(api_key=self.openai_key)
                instr_client = instructor.from_openai(oai_client)
                
                response_obj = await instr_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=ReviewAnalysis,
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": comment}
                    ],
                    temperature=0.1
                )
            except Exception as e:
                logger.info(f"[LLMService] OpenAI sentiment analysis failed: {e}")

        if response_obj:
            return response_obj.model_dump()

        return self._fallback_sentiment_parser(comment)

    def _fallback_sentiment_parser(self, comment: str) -> dict:
        c_lower = comment.lower()
        
        positive_kws = ["good", "great", "excellent", "love", "awesome", "perfect", "durable", "amazing", "best"]
        negative_kws = ["bad", "poor", "terrible", "hate", "worst", "broke", "disappointed", "stiff", "tight"]
        
        pos_count = sum(1 for kw in positive_kws if kw in c_lower)
        neg_count = sum(1 for kw in negative_kws if kw in c_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        tags = []
        for kw in ["durable", "stiff", "lightweight", "heavy", "warm", "waterproof", "comfy", "comfortable", "noisy"]:
            if kw in c_lower:
                tags.append(kw)
        if not tags:
            tags = ["general"]
            
        return {
            "sentiment": sentiment,
            "summary_tags": tags[:3]
        }

    @observe(as_type="generation")
    async def generate_reviews_summary(self, product_name: str, reviews: List[dict]) -> dict:
        if not reviews:
            return {
                "pros": ["No reviews available"],
                "cons": ["No reviews available"],
                "verdict": f"No reviews have been written for {product_name} yet."
            }
            
        context_items = []
        for r in reviews:
            comment = r.get("comment") or "No comment"
            rating = r.get("rating", 3)
            context_items.append(f"- Rating: {rating}/5 stars\n  Review: {comment}")
        context = "\n\n".join(context_items)

        system_prompt = (
            f"You are an expert product analyst summarizing customer feedback for the product: {product_name}.\n"
            "Your goal is to output a structured consensus summary containing pros, cons, and a final verdict based ONLY on the provided reviews context.\n"
            "If no reviews exist or context is empty, return simple placeholders."
        )

        response_obj = None

        if self.groq_key and not self.groq_key.startswith("gsk_mock"):
            try:
                g_client = groq.Groq(api_key=self.groq_key)
                instr_client = instructor.from_groq(g_client)
                
                response_obj = instr_client.chat.completions.create(
                    model=self.groq_model,
                    response_model=ReviewsConsensus,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"=== REVIEWS ===\n{context}"}
                    ],
                    temperature=0.2
                )
            except Exception as e:
                logger.info(f"[LLMService] Groq consensus summary failed: {e}")

        if not response_obj and self.openai_key:
            try:
                oai_client = openai.AsyncOpenAI(api_key=self.openai_key)
                instr_client = instructor.from_openai(oai_client)
                
                response_obj = await instr_client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_model=ReviewsConsensus,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"=== REVIEWS ===\n{context}"}
                    ],
                    temperature=0.2
                )
            except Exception as e:
                logger.info(f"[LLMService] OpenAI consensus summary failed: {e}")

        if response_obj:
            return response_obj.model_dump()

        return self._fallback_reviews_summarizer(product_name, reviews)

    def _fallback_reviews_summarizer(self, product_name: str, reviews: List[dict]) -> dict:
        pros = []
        cons = []
        
        for r in reviews:
            comment_lower = (r.get("comment") or "").lower()
            rating = r.get("rating", 3)
            
            if rating >= 4:
                if "durable" in comment_lower or "quality" in comment_lower:
                    pros.append("Durable and high quality")
                if "comfortable" in comment_lower or "comfy" in comment_lower:
                    pros.append("Comfortable design")
                if "lightweight" in comment_lower:
                    pros.append("Lightweight construction")
            elif rating <= 2:
                if "stiff" in comment_lower or "hard" in comment_lower:
                    cons.append("Some stiffness reported")
                if "tight" in comment_lower or "small" in comment_lower:
                    cons.append("Sizing can feel tight")
                if "broke" in comment_lower or "poor" in comment_lower:
                    cons.append("Durability issues reported")
                    
        pros = list(set(pros)) if pros else ["Good features overall"]
        cons = list(set(cons)) if cons else ["No major complaints"]
        
        avg_rating = sum(r.get("rating", 3) for r in reviews) / len(reviews)
        verdict = f"A solid choice for {product_name} with an average rating of {avg_rating:.1f}/5 stars."
        
        return {
            "pros": pros[:3],
            "cons": cons[:3],
            "verdict": verdict
        }


llm_service = LLMService()
