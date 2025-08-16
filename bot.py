import logging
import threading
from flask import Flask, request, jsonify
import razorpay
from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN, ADMIN_ID, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from db import Base, engine, SessionLocal
from models import Payment

logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Telegram bot command
async def start(update, context):
    await update.message.reply_text("Welcome! Bot is working ✅")

# Razorpay order
@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.json
    amount = int(data.get("amount", 100)) * 100  # INR -> paise
    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": "receipt#1",
        "payment_capture": 1
    })

    db = SessionLocal()
    new_payment = Payment(
        user_id=data.get("user_id", "unknown"),
        amount=amount / 100,
        order_id=order["id"],
        status="created"
    )
    db.add(new_payment)
    db.commit()
    db.close()

    return jsonify(order)

# Razorpay webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    order_id = data.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
    status = data.get("event", "")

    if order_id:
        db = SessionLocal()
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment:
            payment.status = status
            db.commit()
        db.close()

    return jsonify({"status": "ok"})

@app.route("/")
def home():
    return "Flask server alive ✅ and Bot running 🚀"

def run_flask():
    """Run Flask in a background thread."""
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Init DB
    Base.metadata.create_all(bind=engine)

    # Start Flask in a background thread
    threading.Thread(target=run_flask, daemon=True).start()

    # Run Telegram bot in main thread (so signals work properly)
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.run_polling()
