from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, Base
from app.models import User, ShoppingList, ListItem
from app.api.v1.endpoints import users, auth  # <-- ДОБАВИТЬ ИМПОРТ auth

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Подключаем роутеры
app.include_router(users.router)
app.include_router(auth.router)  # <-- ДОБАВИТЬ ПОДКЛЮЧЕНИЕ

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