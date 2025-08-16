from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from utils.text import plans_text
from utils.payments import create_payment_link, PLANS, razorpay_client
from db import SessionLocal, engine, Base
from models import User, Payment
import config
from flask import Flask, request, jsonify
import json
from threading import Thread

# --- Database ---
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- Telegram bot ---
app_bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{plan} - ₹{amount}", callback_data=f"pay_{plan}")]
        for plan, amount in PLANS.items()
    ]
    await update.message.reply_text("Select a plan:", reply_markup=InlineKeyboardMarkup(keyboard))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("Unauthorized ❌")
        return
    msg = " ".join(context.args)
    await update.message.reply_text(f"Broadcasting: {msg}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("pay_", "")
    link = create_payment_link(plan, query.from_user)
    await query.edit_message_text(f"Click to pay for {plan}: {link}")

# Handlers
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("subscribe", subscribe))
app_bot.add_handler(CommandHandler("broadcast", broadcast))
app_bot.add_handler(CallbackQueryHandler(button))

# --- Flask for Razorpay webhook ---
flask_app = Flask(__name__)

@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")

    try:
        razorpay_client.utility.verify_webhook_signature(payload, signature, config.RAZORPAY_WEBHOOK_SECRET)
    except:
        return jsonify({"status": "invalid signature"}), 400

    data = json.loads(payload)
    entity = data["payload"]["payment"]["entity"]

    payment_id = entity["id"]
    amount = entity["amount"] / 100
    status = entity["status"]
    telegram_id = entity["notes"].get("telegram_id")
    plan = entity["notes"].get("plan", "")

    if telegram_id:
        user = db.query(User).filter_by(telegram_id=str(telegram_id)).first()
        if not user:
            user = User(telegram_id=str(telegram_id))
            db.add(user)
            db.commit()
            db.refresh(user)

        user.subscribed = (status == "captured")
        user.plan = plan
        db.commit()

        payment = Payment(user_id=user.id, razorpay_payment_id=payment_id, amount=amount, status=status)
        db.add(payment)
        db.commit()

        # Notify via Telegram
        if status == "captured":
            try:
                app_bot.bot.send_message(chat_id=int(telegram_id), text=f"✅ Payment ₹{amount} for {plan} successful!")
            except:
                pass

    return jsonify({"status": "ok"}), 200

# --- Run both ---
if __name__ == "__main__":
    Thread(target=lambda: app_bot.run_polling()).start()
    flask_app.run(host="0.0.0.0", port=5000)
