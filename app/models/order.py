from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, DateTime, Float, Integer, String, func
from app.core.database import Base

class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    status = Column(String(50), nullable=False, default="pending")   # pending, paid, shipped, cancelled
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Order(id={self.id}, status={self.status}, total={self.total_amount})>"
