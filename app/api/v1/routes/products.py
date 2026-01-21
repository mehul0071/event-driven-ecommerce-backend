from fastapi import APIRouter
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter()

@router.post("/")
async def create_product(product: ProductCreate):
    return ProductResponse(id=1, **product.dict())
