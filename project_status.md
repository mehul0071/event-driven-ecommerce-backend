# Project Status: What Has Been Implemented & What is Left

This document provides a comprehensive report of the implemented features, codebase architecture, and remaining work items in the **Event-Driven AI E-Commerce Backend**.

---

## 1. System Overview

The system is a FastAPI e-commerce backend built with an event-driven AI workflow. Product catalog actions publish events to Redis, and a background worker generates semantic embeddings asynchronously. The application features user authentication, a RAG catalog chatbot, hybrid recommendations, order flows, and a model fine-tuning pipeline.

---

## 2. What Has Been Implemented

### Phase 1: Core E-Commerce & Security
- [x] **User Authentication & Auth Utilities**:
  - Secure password hashing using Argon2/PBKDF2 (`app/core/security.py`).
  - JWT token generation, validation, and decoding (`app/core/security.py`).
  - Access token validation dependency `get_current_user` (`app/api/v1/routes/auth.py`).
  - Register & Login endpoints (`app/api/v1/routes/auth.py`, `app/services/auth_service.py`).
- [x] **Product Catalog Management**:
  - CRUD database routers: create, details, list, update, and delete (`app/api/v1/routes/products.py`, `app/services/product_service.py`).
- [x] **Relational Schema**:
  - SQLAlchemy model definitions for `users`, `products`, `orders`, `order_items`, and `user_interactions` (`app/models/`).

### Phase 2: Event-Driven AI & Semantic Search
- [x] **PostgreSQL pgvector Database Integration**:
  - Column vector extension configured for 384-dimensional dense embeddings (`app/models/product.py`).
- [x] **Redis Event Bus Broker**:
  - Publishing events on product creation (`product_created`) or updates (`product_updated`) (`app/core/event_bus.py`).
  - Fallback mechanisms executing in-memory if Redis connectivity fails (`app/core/event_bus.py`).
- [x] **Asynchronous Embedding Worker**:
  - Standalone daemon (`worker.py`) subscribing to `product_events` to compute embeddings via a local `SentenceTransformer` model (`all-MiniLM-L6-v2`) or Hugging Face cloud APIs, updating the database asynchronously.
- [x] **Semantic Search Endpoint**:
  - Nearest neighbor search query via cosine distance calculations in pgvector (`app/services/product_service.py`).

### Phase 3: Conversational AI & Personalization
- [x] **RAG Customer Support Chatbot**:
  - `/chat` catalog endpoint executing Retrieval-Augmented Generation (`app/api/v1/routes/products.py`).
  - OpenAI / Groq structured output wrapping with the `instructor` library, fallback logic to Hugging Face or offline templates (`app/services/llm_service.py`).
- [x] **Langfuse Observability Tracing**:
  - Integrations using `@observe` to track LLM response accuracy, usage metrics (tokens, time), and retrieval quality.
- [x] **User Taste & Recommendation System**:
  - Logging user catalog interactions (clicks, cart-adds, purchases) (`app/services/interaction_service.py`).
  - Taste vector averaging calculation representing dynamic profiles (`app/services/interaction_service.py`).
  - Personalized hybrid recommendations excluding interacted items and filtering out-of-stock items (`app/services/interaction_service.py`).

### Phase 4: Order Processing & MLOps Pipelines
- [x] **Order Flow APIs**:
  - Placing orders, calculating subtotals/totals, and registering order details (`app/services/order_service.py`).
- [x] **FastAPI Background Tasks Execution**:
  - Running asynchronous operations in-process to simulate stock reservation (`handle_inventory`), billing (`handle_payment`), and confirmation emails (`handle_notification`).
- [x] **Synthetic Fine-Tuning Dataset Generator**:
  - Script (`generate_dataset.py`) formatting merchant catalog data to instruction-response pairs, saved as `train_dataset.json`.
- [x] **LLM Fine-Tuning Pipeline**:
  - SFTTrainer configuration executing LoRA adapters using QLoRA 4-bit NormalFloat quantization (`fine_tune.py`).
- [x] **MLflow Experiment Tracking**:
  - Logging parameters (learning rate, LoRA alpha, model checkpoints) to a SQLite metadata backend (`mlflow.db`).

---

## 3. What is Left / Pending Tasks

### 1. Order Processing Broker Migration (Event-Driven Alignment)
- **Current State**: Placing an order triggers simulated operations in-process using FastAPI `BackgroundTasks`.
- **What is Left**: To make the architecture fully event-driven, the `create_order` method should publish an `order_created` event to a Redis `order_events` channel. A dedicated worker should subscribe to this channel and orchestrate inventory reservation, billing, and notification services independently.

### 2. Fine-Tuned Model Integration (Inference Path)
- **Current State**: The fine-tuning script (`fine_tune.py`) creates and saves LoRA adapter weights (`./fine_tuned_parser`), but the application chatbot and catalog services do not use this adapter.
- **What is Left**: Update `app/services/llm_service.py` to load and run inference through the local fine-tuned adapter weights to parse unstructured input descriptions.

### 3. Queue Retries & Dead-Letter Queue (DLQ)
- **Current State**: If the Redis worker fails to process or encode an embedding (network timeout, API failure), the event is dropped.
- **What is Left**: Implement a robust retry mechanism (e.g., exponential backoff) and route persistently failing events to a Dead-Letter Queue (DLQ) in Redis for audit or manual reprocessing.

### 4. Separate Test Database Configuration
- **Current State**: The test suite shares the development database (`DATABASE_URL`). Running unit tests wipes the database tables (`delete(ProductModel)`), deleting your seeded development catalog items.
- **What is Left**: Configure `pytest` to spin up a separate temporary test database instance (e.g., via docker or `test_db` suffix) during testing so that running tests does not affect development data.

### 5. Frontend UI Client
- **Current State**: The project is a pure FastAPI backend without any user interface.
- **What is Left**: Develop a basic React / Next.js frontend to showcase semantic search results, recommendations, the chatbot interface, and order placement.
