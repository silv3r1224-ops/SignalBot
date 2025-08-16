import os
import threading
import hmac
import hashlib
import json
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import razorpay
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Initialize Flask
app = Flask(__name__)

# Keep track of active subscribers
subscribers = set()

# Telegram Bot
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Function to create Razorpay payment link
def create_payment_link(user_id):
    data = {
        "amount": 10000,  # ₹100
        "currency": "INR",
        "accept_partial": False,
        "description": "Trading Signals Subscription",
        "customer": {"name": f"User {user_id}", "contact": ""},
        "notify": {"sms": False, "email": False},
        "notes": {"telegram_id": str(user_id)},
        "callback_url": "https://YOUR_DOMAIN/razorpay_webhook",
        "callback_method": "post"
    }
    payment_link = razorpay_client.payment_link.create(data)
    return payment_link["short_url"]

# Telegram /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in subscribers:
        await update.message.reply_text("✅ You are subscribed! You will receive trading signals.")
    else:
        payment_link = create_payment_link(user_id)
        await update.message.reply_text(
            f"💰 You are not subscribed yet. Please pay to get access.\n"
            f"Use this link to pay: {payment_link}"
        )

telegram_app.add_handler(CommandHandler("start", start))

# Run Telegram bot in a thread
def run_telegram():
    telegram_app.run_polling()

# Razorpay webhook endpoint
@app.route("/razorpay_webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")

    # Verify webhook signature
    if not signature or not hmac.compare_digest(
        hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest(),
        signature
    ):
        abort(400, "Invalid signature")

    data = json.loads(payload)
    event = data.get("event")

    if event == "payment_link.paid" or event == "payment.captured":
        notes = data.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
        telegram_user_id = int(notes.get("telegram_id", 0))

        if telegram_user_id:
            subscribers.add(telegram_user_id)
            # Notify user
            telegram_app.bot.send_message(
                chat_id=telegram_user_id,
                text="🎉 Payment received! You are now subscribed to trading signals."
            )
            # Notify admin
            telegram_app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"User {telegram_user_id} just subscribed."
            )

    return {"status": "ok"}

# Run Flask
def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_telegram).start()
