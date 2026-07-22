from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.limiter import limiter
from app.api.v1.routes.auth import get_current_user
from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate, DescriptionRequest
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.product_service import create_product, delete_product_by_id, list_of_products, list_product_endpoint_by_id, update_product_by_id, semantic_search_products
from app.services.llm_service import llm_service
from langfuse import observe
from app.schemas.interaction import UserInteractionCreate, UserInteractionResponse
from app.services.interaction_service import log_user_interaction, get_hybrid_recommendations

router = APIRouter()


@router.post("/create-product", response_model=ProductResponse)
async def create_product_endpoint(
    product: ProductCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_product(db, product, background_tasks)


@router.get("/list-products", response_model=List[ProductResponse])
async def list_products_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await list_of_products(db)


@router.get("/list-product/{product_id}", response_model=ProductResponse)
async def list_product_endpoint(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return await list_product_endpoint_by_id(db, product_id)


@router.patch("/update-product/{product_id}", response_model=ProductUpdate)
async def update_product(
    product_id: UUID,
    update_product: ProductUpdate,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await update_product_by_id(db, product_id, update_product, background_tasks)


@router.delete("/delete-product/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    await delete_product_by_id(db, product_id)


@router.get("/search", response_model=List[ProductResponse])
@limiter.limit("10/minute")
async def search_products(
    request: Request,
    query: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    return await semantic_search_products(db, query, limit)


@router.post("/chat", response_model=ChatResponse)
@observe(name="chat_with_catalog")
@limiter.limit("10/minute")
async def chat_with_catalog(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("langfuse.trace.tags", ["rag_chatbot_query"])
            current_span.set_attribute("langfuse.trace.input", chat_request.query)
    except Exception:
        pass

    products = await semantic_search_products(db, chat_request.query, chat_request.limit)
    bot_response = await llm_service.generate_rag_response(chat_request.query, products)
    
    return ChatResponse(
        answer=bot_response.response,
        recommended_product_ids=bot_response.recommended_product_ids,
        follow_up_questions=bot_response.follow_up_questions,
        retrieved_products=products
    )


@router.post("/interactions", response_model=UserInteractionResponse)
async def log_interaction(
    interaction: UserInteractionCreate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await log_user_interaction(db, current_user.id, interaction)


@router.get("/recommendations", response_model=List[ProductResponse])
async def recommend_products(
    limit: int = 5,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_hybrid_recommendations(db, current_user.id, limit)


@router.post("/parse-description")
@limiter.limit("10/minute")
async def parse_product_description_endpoint(
    request: Request,
    description_request: DescriptionRequest,
    current_user = Depends(get_current_user)
):
    parsed_attributes = await llm_service.parse_product_description(description_request.description)
    return parsed_attributes


@router.post("/parse-and-create-product", response_model=ProductResponse)
async def parse_and_create_product_endpoint(
    description_request: DescriptionRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    parsed = await llm_service.parse_product_description(description_request.description)
    product_create = ProductCreate(
        name=parsed.get("name") or "parsed-product",
        description=f"Color: {parsed.get('color')}, Size: {parsed.get('size')}, Category: {parsed.get('category')}",
        price=float(parsed.get("price") or 0.0),
        stock=int(parsed.get("stock") or 0)
    )
    return await create_product(db, product_create, background_tasks)