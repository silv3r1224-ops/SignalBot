import os
import asyncio
import logging
import hmac
import hashlib
import json
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import razorpay

# ------------------------
# Logging
# ------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------
# Environment Variables
# ------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
PORT = int(os.getenv("PORT", 5000))

# Check required env vars
required_vars = [TELEGRAM_TOKEN, ADMIN_ID, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET]
if not all(required_vars):
    logger.error("One or more environment variables are missing!")
    raise SystemExit("Please set all required environment variables.")

# ------------------------
# Razorpay client
# ------------------------
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ------------------------
# Flask App
# ------------------------
app = Flask(__name__)

# ------------------------
# Subscribers
# ------------------------
subscribers = set()

# ------------------------
# Telegram Bot
# ------------------------
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in subscribers:
        await update.message.reply_text("✅ You are subscribed! You will receive trading signals.")
    else:
        order_data = {
            "amount": 10000,  # ₹100
            "currency": "INR",
            "receipt": f"user_{user_id}",
            "payment_capture": 1,
            "notes": {"telegram_id": str(user_id)}
        }
        order = razorpay_client.order.create(data=order_data)
        payment_link = f"https://checkout.razorpay.com/v1/checkout.js?order_id={order['id']}"
        await update.message.reply_text(
            f"💰 You are not subscribed yet. Please pay to get access.\n"
            f"Use this link to pay: {payment_link}"
        )

telegram_app.add_handler(CommandHandler("start", start))

# ------------------------
# Razorpay Webhook
# ------------------------
@app.route("/razorpay_webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    
    # Verify webhook
    if not signature or not hmac.new(
        bytes(RAZORPAY_WEBHOOK_SECRET, 'utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest() == signature:
        logger.warning("Invalid Razorpay signature")
        abort(400, "Invalid signature")
    
    data = json.loads(payload)
    event = data.get("event")
    
    if event == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]
        notes = payment_entity.get("notes", {})
        telegram_user_id = int(notes.get("telegram_id", 0))
        
        if telegram_user_id:
            subscribers.add(telegram_user_id)
            asyncio.run(send_telegram_messages(telegram_user_id))
    
    return {"status": "ok"}

async def send_telegram_messages(user_id: int):
    try:
        await telegram_app.bot.send_message(
            chat_id=user_id,
            text="🎉 Payment received! You are now subscribed to trading signals."
        )
        if ADMIN_ID:
            await telegram_app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"User {user_id} just subscribed."
            )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

# ------------------------
# Run Flask
# ------------------------
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ------------------------
# Run Telegram
# ------------------------
def run_telegram():
    # Run Telegram bot in main asyncio loop
    asyncio.run(telegram_app.run_polling())

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    import threading
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_telegram).start()
    logger.info("Bot and Flask server started successfully.")
