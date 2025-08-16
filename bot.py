import razorpay
from flask import Flask, request
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import User, Payment
import config
import hmac, hashlib, json

# Setup DB
Base.metadata.create_all(bind=engine)

# Razorpay client
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

# Flask app
app = Flask(__name__)

# Telegram bot app
app_bot = Application.builder().token(config.BOT_TOKEN).build()

# -------- Telegram Handlers -------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    db: Session = SessionLocal()
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id)
        db.add(user)
        db.commit()
    db.close()
    await update.message.reply_text("Welcome! 🎉 Use /subscribe to start subscription.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    db: Session = SessionLocal()
    user = db.query(User).filter_by(telegram_id=telegram_id).first()

    order = razorpay_client.order.create({
        "amount": 10000,  # ₹100.00 in paise
        "currency": "INR",
        "payment_capture": "1"
    })

    payment = Payment(order_id=order["id"], user=user)
    db.add(payment)
    db.commit()
    db.close()

    pay_url = f"https://rzp.io/l/{order['id']}"
    await update.message.reply_text(f"Pay ₹100 to subscribe:\n{pay_url}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return await update.message.reply_text("Not authorized ❌")
    
    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("Usage: /broadcast <message>")
    
    db: Session = SessionLocal()
    users = db.query(User).all()
    db.close()
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=msg)
        except:
            pass
    
    await update.message.reply_text("✅ Broadcast sent")

# -------- Flask Routes -------- #

@app.route("/", methods=["GET"])
def home():
    return "Bot & Razorpay server is running ✅"

@app.route("/razorpay/webhook", methods=["POST"])
def webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    
    try:
        hmac_obj = hmac.new(
            bytes(config.RAZORPAY_WEBHOOK_SECRET, "utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        )
        generated_sig = hmac_obj.hexdigest()
        if generated_sig != signature:
            return "Invalid signature", 400
    except Exception as e:
        return str(e), 400
    
    data = json.loads(payload)
    if data.get("event") == "payment.captured":
        order_id = data["payload"]["payment"]["entity"]["order_id"]
        payment_id = data["payload"]["payment"]["entity"]["id"]

        db: Session = SessionLocal()
        payment = db.query(Payment).filter_by(order_id=order_id).first()
        if payment:
            payment.status = "captured"
            payment.payment_id = payment_id
            payment.user.is_subscribed = True
            db.commit()
        db.close()
    return "OK", 200

# -------- Run both -------- #

if __name__ == "__main__":
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("subscribe", subscribe))
    app_bot.add_handler(CommandHandler("broadcast", broadcast))

    Thread(target=lambda: app_bot.run_polling()).start()
    app.run(host="0.0.0.0", port=5000)
