class Config:
    # Telegram
    ADMIN_ID = 7909563220
    BOT_TOKEN = "8250035384:AAHbSjhqT0fODfQHnjgBFcZLuIQeaUBJeP8"

    # Razorpay
    RAZORPAY_KEY_ID = "rzp_test_R5a8j8yy3WEssP"
    RAZORPAY_KEY_SECRET = "DNSIjreZrmVcqsP0n6goeAoq"
    RAZORPAY_WEBHOOK_SECRET = "#Tesan25"

    # Database (SQLite local file)
    SQLALCHEMY_DATABASE_URI = "sqlite:///bot.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Webhook URL
    WEBHOOK_URL = "https://signalbot-tfnb.onrender.com/telegram-webhook"
