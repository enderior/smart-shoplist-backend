from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base

# Создаём таблицы в базе данных (временно, для разработки)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
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
