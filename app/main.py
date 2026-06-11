from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import automations, game, health, integrations, learning, notion, subscriptions, ui, work_knowledge
from app.core.config import settings
from app.core.database import initialize_database
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    initialize_database()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.include_router(automations.router)
app.include_router(game.router)
app.include_router(health.router)
app.include_router(integrations.router)
app.include_router(learning.router)
app.include_router(notion.router)
app.include_router(subscriptions.router)
app.include_router(ui.router)
app.include_router(work_knowledge.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
