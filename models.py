from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    subscribed = Column(Boolean, default=False)
    plan = Column(String, nullable=True)

    payments = relationship("Payment", back_populates="user")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    razorpay_payment_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False)

    user = relationship("User", back_populates="payments")
