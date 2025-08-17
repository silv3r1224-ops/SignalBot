import os
import logging
import hmac
import hashlib
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import razorpay
import asyncio

# --------------------------
# Load .env
# --------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
PORT = int(os.getenv("PORT", 5000))

# --------------------------
# Logging
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------
# Razorpay client
# --------------------------
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

# --------------------------
# Flask app
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Home route accessed")
    return "Bot & Server Running!"

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    data = request.data
    signature = request.headers.get('X-Razorpay-Signature', '')

    generated_signature = hmac.new(
        bytes(RAZORPAY_WEBHOOK_SECRET, 'utf-8'),
        msg=data,
        digestmod=hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(generated_signature, signature):
        logger.info(f"Verified webhook: {request.json}")
        # Notify admin
        asyncio.create_task(telegram_app.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Payment received: {request.json}"
        ))
        return jsonify({"status": "ok"}), 200
    else:
        logger.warning("Invalid webhook signature")
        return jsonify({"status": "error", "message": "Invalid signature"}), 400

# --------------------------
# Telegram bot
# --------------------------
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is running ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = 10000  # in paise (₹100)
    currency = "INR"
    
    # Create Razorpay order
    order = razorpay_client.order.create({
        "amount": amount,
        "currency": currency,
        "payment_capture": 1
    })
    
    await update.message.reply_text(
        f"Please pay ₹{amount/100} using Razorpay.\n"
        f"Order ID: {order['id']}\n"
        f"Use your frontend/payment page to complete payment.\n"
        f"Webhook will verify automatically."
    )

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("pay", pay))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Main async
# --------------------------
async def main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram bot started")
    
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = [f"0.0.0.0:{PORT}"]
    await serve(app, config)

    await telegram_app.stop()
    await telegram_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
