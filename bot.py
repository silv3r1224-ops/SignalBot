import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from hypercorn.asyncio import serve
from hypercorn.config import Config

# --------------------------
# Logging setup
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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
    raise RuntimeError("TELEGRAM_TOKEN environment variable not set!")

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update, context):
    await update.message.reply_text("Hello! Bot is running ✅")
    logger.info(f"/start used by {update.effective_user.username}")

async def echo(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")
    logger.info(f"Message from {update.effective_user.username}: {update.message.text}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Main async function
# --------------------------
async def main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram bot started")
    
    # Run Flask using Hypercorn
    port = int(os.environ.get("PORT", 5000))
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)

    # Gracefully stop Telegram bot if Flask stops
    await telegram_app.stop()
    await telegram_app.shutdown()

# --------------------------
# Start safely in existing loop
# --------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
