import os
import threading
import hmac
import hashlib
import json
from flask import Flask, request, abort
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import razorpay

# Load environment variables
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

# Function to create Razorpay payment link for a user
def create_payment_link(user_id):
    order_data = {
        "amount": 10000,  # ₹100
        "currency": "INR",
        "receipt": f"user_{user_id}",
        "payment_capture": 1,
        "notes": {"telegram_id": str(user_id)}
    }
    order = razorpay_client.order.create(data=order_data)
    payment_link = f"https://checkout.razorpay.com/v1/checkout.js?order_id={order['id']}"
    return payment_link

# Telegram command: start
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

# Run Telegram in separate thread
def run_telegram():
    telegram_app.run_polling()

# Razorpay webhook endpoint
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
        abort(400, "Invalid signature")
    
    data = json.loads(payload)
    event = data.get("event")
    
    if event == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]
        notes = payment_entity.get("notes", {})
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
