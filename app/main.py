from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.database import engine, Base
from app.models import order, product

app = FastAPI(title="Event-Driven E-Commerce")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "ok"}
