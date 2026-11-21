from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal, engine
from .errors import register_error_handlers
from .models import Base
from .routers import cinemas, movies
from .seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates tables if they don't exist yet (supabase/schema.sql does the same
    # thing and also enables row level security; running either is fine).
    Base.metadata.create_all(engine)
    if get_settings().seed_sample_data:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(
    title="Doomsday Ready API",
    description="Plan your MCU rewatch and book an opening-night watch party.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

api = APIRouter(prefix="/api")
api.include_router(movies.router)
api.include_router(cinemas.router)


@api.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api)
