from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.models import User, ShoppingList, ListItem, PurchaseHistory
from app.api.v1.endpoints import users, auth, lists, recommendations, purchase_history

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Таблицы создаются через Alembic, автоматическое создание отключено
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(lists.router)
app.include_router(recommendations.router)
app.include_router(purchase_history.router)

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