# bot.py
import hmac, hashlib, json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from utils.text import plans_text
from db import SessionLocal, engine, Base
from models import User, Payment
import config
import razorpay
from flask import Flask, request, jsonify

# Initialize DB
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Telegram bot
app_bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

# Razorpay client
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Select a plan:\n"
        "Basic: https://rzp.io/i/basiclink\n"
        "Standard: https://rzp.io/i/standardlink\n"
        "Premium: https://rzp.io/i/premiumlink"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)
    await update.message.reply_text(f"Broadcasting: {message}")

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("subscribe", subscribe))
app_bot.add_handler(CommandHandler("broadcast", broadcast))

# Flask webhook
flask_app = Flask(__name__)

@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    secret = config.RAZORPAY_WEBHOOK_SECRET

    # Verify signature
    try:
        hmac.new(bytes(secret, 'utf-8'), msg=payload, digestmod=hashlib.sha256).hexdigest()
        razorpay_client.utility.verify_webhook_signature(payload, signature, secret)
    except:
        return jsonify({"status": "invalid signature"}), 400

    data = json.loads(payload)
    event = data.get("event")
    payment_id = data["payload"]["payment"]["entity"]["id"]
    amount = data["payload"]["payment"]["entity"]["amount"] / 100
    status = data["payload"]["payment"]["entity"]["status"]
    telegram_id = data["payload"]["payment"]["entity"]["notes"].get("telegram_id")  # store telegram_id in notes

    if telegram_id:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
        if not user:
            user = User(telegram_id=str(telegram_id))
            db.add(user)
            db.commit()
            db.refresh(user)
        user.subscribed = status == "captured"
        user.plan = data["payload"]["payment"]["entity"]["notes"].get("plan", "")
        db.add(user)
        db.commit()

        # Save payment
        payment = Payment(user_id=user.id, razorpay_payment_id=payment_id, amount=amount, status=status)
        db.add(payment)
        db.commit()
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    from threading import Thread
    # Run Telegram bot
    Thread(target=lambda: app_bot.run_polling()).start()
    # Run Flask server
    flask_app.run(host="0.0.0.0", port=5000)
