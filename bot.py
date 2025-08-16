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
        # Add Razorpay signature verification if needed
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

# Example command handler
async def start(update, context):
    try:
        await update.message.reply_text("Hello! Bot is running ✅")
        logger.info(f"/start used by {update.effective_user.username}")
    except Exception as e:
        logger.error(f"Error in /start handler: {e}")

# Example message handler
async def echo(update, context):
    try:
        await update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Message from {update.effective_user.username}: {update.message.text}")
    except Exception as e:
        logger.error(f"Error in echo handler: {e}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Safe polling with auto-restart
# --------------------------
async def run_telegram():
    while True:
        try:
            logger.info("Starting Telegram polling...")
            await telegram_app.run_polling()
        except Exception as e:
            logger.error(f"Telegram polling crashed: {e}")
            logger.info("Restarting Telegram polling in 5s...")
            await asyncio.sleep(5)

# --------------------------
# Main function to run bot + server
# --------------------------
if __name__ == "__main__":
    async def main():
        # Run Telegram bot in background
        asyncio.create_task(run_telegram())
        # Run Flask server
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"Starting Flask server on port {port}")
        app.run(host="0.0.0.0", port=port)

    logger.info("Bot and Flask server starting...")
    asyncio.run(main())
