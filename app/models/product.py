from sqlalchemy import Column, Integer, String, Float, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class ProductModel(Base):
    __tablename__ = "products"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.uuid_generate_v4(),
        nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<ProductModel(id={self.id}, name={self.name}, price={self.price}, stock={self.stock})>" 