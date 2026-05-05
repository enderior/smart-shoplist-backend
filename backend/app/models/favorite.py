from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class FavoriteItem(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("list_items.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
