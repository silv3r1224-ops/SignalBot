# models.py
from sqlalchemy import Column, Integer, String, Boolean, Float
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    plan = Column(String, nullable=True)
    subscribed = Column(Boolean, default=False)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    razorpay_payment_id = Column(String)
    amount = Column(Float)
    status = Column(String)
