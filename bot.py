import logging
import asyncio
from flask import Flask, request, jsonify
import razorpay
from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN, ADMIN_ID, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from db import Base, engine, SessionLocal
from models import Payment

logging.basicConfig(level=logging.INFO)

# =========================
# Flask app
# =========================
app = Flask(__name__)

# Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Telegram bot command
async def start(update, context):
    await update.message.reply_text("Welcome! Bot is working ✅")

# Build bot
def build_bot():
    Base.metadata.create_all(bind=engine)
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    return app_bot

# =========================
# Razorpay order endpoint
# =========================
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
        amount=amount/100,
        order_id=order["id"],
        status="created"
    )
    db.add(new_payment)
    db.commit()
    db.close()

    return jsonify(order)

# =========================
# Razorpay webhook endpoint
# =========================
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

# =========================
# Main async runner
# =========================
async def main():
    bot_app = build_bot()

    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = ["0.0.0.0:5000"]

    await asyncio.gather(
        bot_app.run_polling(),   # Telegram bot
        serve(app, config)       # Flask API with Hypercorn
    )

if __name__ == "__main__":
    asyncio.run(main())
