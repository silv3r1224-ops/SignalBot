# bot.py

import os
import json
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from utils.text import plans_text
from utils.payments import create_payment_link, PLANS
from db import SessionLocal, engine, Base
from models import User, Payment
import razorpay
import config

# ------------------- Database Setup -------------------
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ------------------- Telegram Bot Setup -------------------
app_bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"{plan} - ₹{amount}", callback_data=f"pay_{plan}")] for plan, amount in PLANS.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a plan to pay:", reply_markup=reply_markup)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)
    await update.message.reply_text(f"Broadcasting: {message}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_name = query.data.replace("pay_", "")
    link = create_payment_link(plan_name, query.from_user)
    await query.edit_message_text(f"Click this link to pay for {plan_name}: {link}")

# Add handlers
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("subscribe", subscribe))
app_bot.add_handler(CommandHandler("broadcast", broadcast))
app_bot.add_handler(CallbackQueryHandler(button))

# ------------------- Razorpay Setup -------------------
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

# ------------------- Flask App Setup -------------------
flask_app = Flask(__name__)

@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    secret = config.RAZORPAY_WEBHOOK_SECRET

    try:
        razorpay_client.utility.verify_webhook_signature(payload, signature, secret)
    except:
        return jsonify({"status": "invalid signature"}), 400

    data = json.loads(payload)
    payment_entity = data["payload"]["payment"]["entity"]
    payment_id = payment_entity["id"]
    amount = payment_entity["amount"] / 100
    status = payment_entity["status"]
    telegram_id = payment_entity["notes"].get("telegram_id")
    plan = payment_entity["notes"].get("plan", "")

    if telegram_id:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
        if not user:
            user = User(telegram_id=str(telegram_id))
            db.add(user)
            db.commit()
            db.refresh(user)
        user.subscribed = status == "captured"
        user.plan = plan
        db.add(user)
        db.commit()

        payment = Payment(user_id=user.id, razorpay_payment_id=payment_id, amount=amount, status=status)
        db.add(payment)
        db.commit()

        # Notify user on Telegram
        if status == "captured":
            try:
                Thread(target=lambda: app_bot.bot.send_message(
                    chat_id=int(telegram_id),
                    text=f"✅ Payment of ₹{amount} for {plan} plan successful! You are now subscribed."
                )).start()
            except:
                pass

    return jsonify({"status": "success"}), 200

# ------------------- Run Flask App -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render requires this
    # Run Telegram Bot in a separate thread
    Thread(target=lambda: app_bot.run_polling()).start()
    flask_app.run(host="0.0.0.0", port=port)
