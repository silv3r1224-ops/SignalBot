import os

# Telegram bot token
BOT_TOKEN = "8250035384:AAHbSjhqT0fODfQHnjgBFcZLuIQeaUBJeP8"

# Admin Telegram user ID
ADMIN_ID = 7909563220

# Database URL (SQLite)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///signalbot.db")
