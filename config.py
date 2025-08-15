import os
from datetime import timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///signalbot.db")

# Plans (INR)
PLANS = {
    "bronze": {"name": "Bronze", "price_inr": 199, "duration": timedelta(days=30)},
    "silver": {"name": "Silver", "price_inr": 499, "duration": timedelta(days=90)},
    "gold":   {"name": "Gold",   "price_inr": 1499, "duration": timedelta(days=365)},
}

def payments_enabled() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
