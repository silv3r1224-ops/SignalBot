import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --------------------------
# Logging setup
# --------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# Flask setup
# --------------------------
app = Flask(__name__)

@app.route("/")
def home():
    logger.info("Home route accessed")
    return "Bot & Server Running!"

# --------------------------
# Telegram bot setup
# --------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable not set!")

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
bot = telegram_app.bot  # Needed for webhook handling

# --------------------------
# Bot commands
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is running ✅")
    logger.info(f"/start used by {update.effective_user.username}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")
    logger.info(f"Message from {update.effective_user.username}: {update.message.text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Webhook route
# --------------------------
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Receive updates from Telegram via webhook"""
    update = Update.de_json(request.get_json(), bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok", 200

# --------------------------
# Set webhook on startup
# --------------------------
async def set_webhook():
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook/{TELEGRAM_TOKEN}"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

# --------------------------
# Run Flask & bot
# --------------------------
if __name__ == "__main__":
    import asyncio

    # Set webhook first
    asyncio.run(set_webhook())

    # Run Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
