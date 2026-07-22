from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.core.database import engine, Base
import uuid
from app.core.logging_config import setup_logging, request_id_var
from app.models import order, product
from app.core.event_bus import event_bus

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await event_bus.connect()
    yield
    await event_bus.close()

app = FastAPI(title="Event-Driven E-Commerce", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_var.set(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    request_id_var.reset(token)
    return response

@app.get("/")
async def root():
    return {"status": "ok"}
