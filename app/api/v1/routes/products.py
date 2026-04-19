from fastapi import APIRouter
from app.schemas.product import ProductCreate, ProductResponse

router = APIRouter()

@router.post("/create-product")
async def create_product(product: ProductCreate):
    return ProductResponse(id=1, **product.dict())
