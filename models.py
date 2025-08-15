from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint
from datetime import datetime
import enum

class Base(DeclarativeBase):
    pass

class PaymentStatus(str, enum.Enum):
    created = "created"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # Telegram user id
    username: Mapped[str | None] = mapped_column(String(64))
    chat_id: Mapped[int | None] = mapped_column(Integer)  # PM chat id == user id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_key: Mapped[str] = mapped_column(String(32))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user = relationship("User", back_populates="subscriptions")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_key: Mapped[str] = mapped_column(String(32))
    amount_inr: Mapped[int] = mapped_column(Integer)
    rp_link_id: Mapped[str | None] = mapped_column(String(64))   # Razorpay Payment Link ID (plink_*)
    rp_short_url: Mapped[str | None] = mapped_column(String(256))
    rp_payment_id: Mapped[str | None] = mapped_column(String(64)) # pay_*
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.created)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("rp_link_id", name="uq_rp_link"),)
