from sqlalchemy import Column, Integer, String, Float, DateTime, func
from db import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="created")
    order_id = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
