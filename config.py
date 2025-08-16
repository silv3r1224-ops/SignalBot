import os

ADMIN_ID = int(os.getenv("ADMIN_ID", "7909563220"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "8250035384:AAHbSjhqT0fODfQHnjgBFcZLuIQeaUBJeP8")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_R5a8j8yy3WEssP")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "DNSIjreZrmVcqsP0n6goeAoq")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "#Tesan25")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///signalbot.db")
