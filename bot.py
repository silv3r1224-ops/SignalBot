import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import razorpay
import hmac
import hashlib
from db import SessionLocal
from models import Payment

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# Initialize Flask app
app = Flask(__name__)

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Initialize Telegram bot application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Telegram command handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /pay <amount> to make a payment.\nExample: /pay 100"
    )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Please provide a valid amount. Example: /pay 100")
        return

    amount = int(context.args[0]) * 100  # Razorpay uses paise
    user_id = update.effective_chat.id

    # Create Razorpay order
    order = razorpay_client.order.create(dict(amount=amount, currency="INR", payment_capture="1"))

    # Save order in DB
    db = SessionLocal()
    payment = Payment(user_id=user_id, razorpay_order_id=order['id'], amount=amount, status="created")
    db.add(payment)
    db.commit()
    db.close()

    # Send payment link
    keyboard = [
        [InlineKeyboardButton("Pay Now", url=f"https://rzp.io/i/{order['id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Click below to pay:", reply_markup=reply_markup)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("pay", pay))

# --- Flask webhook for Razorpay ---

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature")

    # Verify webhook
    try:
        hmac.new(
            bytes(RAZORPAY_KEY_SECRET, 'utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
    except Exception as e:
        return "Signature verification failed", 400

    data = request.json
    if data.get("event") == "payment.captured":
        order_id = data["payload"]["payment"]["entity"]["order_id"]
        db = SessionLocal()
        payment = db.query(Payment).filter_by(razorpay_order_id=order_id).first()
        if payment:
            payment.status = "paid"
            db.commit()
            # Notify user on Telegram
            telegram_app.bot.send_message(chat_id=payment.user_id, text="✅ Payment successful!")
        db.close()

    return "OK", 200

# --- Run both Telegram and Flask ---

def run_telegram():
    telegram_app.run_polling()

if __name__ == "__main__":
    import threading
    # Run Telegram bot in separate thread
    t = threading.Thread(target=run_telegram)
    t.start()
    # Run Flask server for webhook
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
