from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import Base, User, Subscription, Payment, PaymentStatus
from config import DB_URL, PLANS

engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

def init_db():
    Base.metadata.create_all(engine)

def upsert_user(user_id: int, username: str | None, chat_id: int | None):
    with SessionLocal() as s:
        u = s.get(User, user_id)
        if not u:
            u = User(id=user_id, username=username, chat_id=chat_id)
            s.add(u)
        else:
            changed = False
            if username and u.username != username:
                u.username = username
                changed = True
            if chat_id and u.chat_id != chat_id:
                u.chat_id = chat_id
                changed = True
            if changed:
                s.add(u)
        s.commit()
        return u

def is_banned(user_id: int) -> bool:
    with SessionLocal() as s:
        u = s.get(User, user_id)
        return bool(u and u.banned)

def set_banned(user_id: int, banned: bool):
    with SessionLocal() as s:
        u = s.get(User, user_id) or User(id=user_id)
        u.banned = banned
        s.add(u)
        s.commit()

def get_active_until(user_id: int):
    with SessionLocal() as s:
        q = (
            s.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.active == True)
            .order_by(Subscription.end_at.desc())
        )
        last = q.first()
        return last.end_at if last else None

def activate_subscription(user_id: int, plan_key: str):
    from datetime import timedelta
    now = datetime.utcnow()
    current_until = get_active_until(user_id)
    start = now if not current_until or current_until < now else current_until
    end = start + PLANS[plan_key]["duration"]
    with SessionLocal() as s:
        sub = Subscription(user_id=user_id, plan_key=plan_key, start_at=start, end_at=end, active=True)
        s.add(sub)
        s.commit()
        return sub

def create_payment(user_id: int, plan_key: str, amount_inr: int, link_id: str, short_url: str):
    with SessionLocal() as s:
        p = Payment(
            user_id=user_id,
            plan_key=plan_key,
            amount_inr=amount_inr,
            rp_link_id=link_id,
            rp_short_url=short_url,
            status=PaymentStatus.created,
        )
        s.add(p)
        s.commit()
        return p

def mark_payment_paid(link_id: str, payment_id: str | None):
    with SessionLocal() as s:
        p = s.query(Payment).filter(Payment.rp_link_id == link_id).first()
        if not p:
            return None
        p.status = PaymentStatus.paid
        p.rp_payment_id = payment_id
        s.commit()
        return p

def iter_all_user_chat_ids():
    with SessionLocal() as s:
        for (cid,) in s.query(User.chat_id).filter(User.chat_id.isnot(None)).all():
            yield cid

def stats():
    with SessionLocal() as s:
        total_users = s.query(User).count()
        active_subs = s.query(Subscription).filter(Subscription.active==True).count()
        total_payments = s.query(Payment).count()
        return {"users": total_users, "active_subscriptions": active_subs, "payments": total_payments}
