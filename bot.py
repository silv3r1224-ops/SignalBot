import logging, json, hmac, hashlib
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from db import SessionLocal, engine, Base
from models import User, Payment
from utils.text import plans_text
from utils.payments import create_payment_link, PLANS
import config
import razorpay

# Logging
logging.basicConfig(level=logging.INFO)

# Database
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Flask
flask_app = Flask(__name__)

# Telegram bot
application = Application.builder().token(config.BOT_TOKEN).build()

# Razorpay client
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

# --- Telegram Commands ---
async def start(update: Update, context):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context):
    keyboard = [[InlineKeyboardButton(f"{p} - ₹{a}", callback_data=f"pay_{p}")] for p, a in PLANS.items()]
    await update.message.reply_text("Choose a plan:", reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast(update: Update, context):
    if str(update.effective_user.id) != config.ADMIN_CHAT_ID:
        await update.message.reply_text("Unauthorized!")
        return
    msg = " ".join(context.args)
    users = db.query(User).all()
    for u in users:
        try:
            await application.bot.send_message(chat_id=int(u.telegram_id), text=msg)
        except:
            continue
    await update.message.reply_text("✅ Broadcast sent.")

# --- Button Callback ---
async def button(update: Update, context):
    q = update.callback_query
    await q.answer()
    plan = q.data.replace("pay_", "")
    link = create_payment_link(plan, q.from_user)
    await q.edit_message_text(f"Pay for {plan}: {link}")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("subscribe", subscribe))
application.add_handler(CommandHandler("broadcast", broadcast))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

# --- Razorpay Webhook ---
@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    sig = request.headers.get("X-Razorpay-Signature")
    secret = config.RAZORPAY_WEBHOOK_SECRET
    try:
        razorpay_client.utility.verify_webhook_signature(payload, sig, secret)
    except:
        return jsonify({"status": "invalid signature"}), 400

    data = json.loads(payload)
    payment = data["payload"]["payment"]["entity"]
    tid = payment["notes"].get("telegram_id")
    plan = payment["notes"].get("plan", "")
    status = payment["status"]

    if tid:
        user = db.query(User).filter_by(telegram_id=str(tid)).first()
        if not user:
            user = User(telegram_id=str(tid), name="User")
            db.add(user)
        user.subscribed = status == "captured"
        user.plan = plan
        db.commit()

        pay = Payment(
            user_id=user.id,
            razorpay_payment_id=payment["id"],
            amount=payment["amount"]/100,
            status=status
        )
        db.add(pay)
        db.commit()

        if status == "captured":
            Thread(target=lambda: application.bot.send_message(
                chat_id=int(tid),
                text=f"✅ Payment successful for {plan} plan!"
            )).start()

    return jsonify({"status": "success"}), 200

# --- Run ---
if __name__ == "__main__":
    Thread(target=lambda: application.run_polling()).start()
    flask_app.run(host="0.0.0.0", port=5000)
