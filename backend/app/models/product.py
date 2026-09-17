from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # как ввёл пользователь
    normalized_name = Column(String(255), unique=True, nullable=False, index=True)  # lower/strip
    created_at = Column(DateTime(timezone=True), server_default=func.now())
