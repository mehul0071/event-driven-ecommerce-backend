import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class UserInteractionModel(Base):
    __tablename__ = "user_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(50), nullable=False)  # "click", "view", "purchase"
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("UserModel")
    product = relationship("ProductModel")

    def __repr__(self):
        return f"<UserInteraction(user_id={self.user_id}, product_id={self.product_id}, type={self.interaction_type})>"
