import os
import logging
import asyncio
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

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update, context):
    try:
        await update.message.reply_text("Hello! Bot is running ✅")
        logger.info(f"/start used by {update.effective_user.username}")
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")

async def echo(update, context):
    try:
        await update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Message from {update.effective_user.username}: {update.message.text}")
    except Exception as e:
        logger.error(f"Error in echo handler: {e}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Main function to run bot + Flask
# --------------------------
async def main():
    # Start Telegram polling
    telegram_task = asyncio.create_task(telegram_app.run_polling())

    # Start Flask using Hypercorn (async-friendly)
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', 5000)}"]

    await hypercorn.asyncio.serve(app, config)

    # Wait for telegram to finish (never)
    await telegram_task

if __name__ == "__main__":
    logger.info("Bot and Flask server starting...")
    asyncio.run(main())
