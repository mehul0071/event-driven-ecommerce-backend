from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.database import engine, Base

app = FastAPI(title="Event-Driven E-Commerce")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "ok"}
