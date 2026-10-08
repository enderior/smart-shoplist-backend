from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ContactChangeToken(Base):
    __tablename__ = "contact_change_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    change_type = Column(String(10), nullable=False)  # "email" | "phone"
    new_value = Column(String(255), nullable=False)  # куда меняем
    code = Column(String(6), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
