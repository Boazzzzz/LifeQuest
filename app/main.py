from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, integrations, learning
from app.core.config import settings
from app.core.database import initialize_database
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(integrations.router)
app.include_router(learning.router)
