from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base

# 👇 ВАЖНО: импортируем модели, чтобы Base знал о них
from app.models import User, ShoppingList, ListItem

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

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