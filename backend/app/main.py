import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine
from app import models  # noqa: F401 — регистрирует все модели в Base.metadata
from app.api.v1.endpoints import users, auth, lists, recommendations, purchase_history, search, shared_lists


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Таблицы создаются через Alembic
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# ФИКС #6: создаём папку до mount
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(users.router)
app.include_router(lists.router)
app.include_router(shared_lists.router)
app.include_router(recommendations.router)
app.include_router(search.router)
app.include_router(purchase_history.router)
app.include_router(auth.router)


@app.get("/")
async def root():
    return {
        "message": "Smart ShopList API",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
