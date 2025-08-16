import os
import logging
import asyncio
import threading
from flask import Flask, request, jsonify
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# --------------------------
# Logging setup
# --------------------------
LOG_FILE = "bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------------------
# Flask setup
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Home route accessed")
    return "Bot & Server Running!"

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    try:
        data = request.json
        logger.info(f"Webhook received: {data}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# --------------------------
# Telegram Bot setup
# --------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set!")
    raise RuntimeError("TELEGRAM_TOKEN environment variable not set!")

async def start(update, context):
    await update.message.reply_text("Hello! Bot is running ✅")
    logger.info(f"/start used by {update.effective_user.username}")

async def echo(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")
    logger.info(f"Message from {update.effective_user.username}: {update.message.text}")

# --------------------------
# Function to run Telegram bot with auto-restart
# --------------------------
async def run_telegram_bot():
    while True:
        try:
            telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            telegram_app.add_handler(CommandHandler("start", start))
            telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

            logger.info("Telegram bot starting...")
            await telegram_app.run_polling()
        except Exception as e:
            logger.error(f"Bot crashed: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)

# --------------------------
# Run Flask in a separate thread
# --------------------------
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --------------------------
# Entry point
# --------------------------
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    logger.info("Flask server started in a separate thread")

    # Run Telegram bot
    asyncio.run(run_telegram_bot())
