import os
import asyncio
import logging
from flask import Flask, request, jsonify, render_template
from threading import Thread
import razorpay
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import db, User, Payment
from config import Config

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

# Razorpay client
razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))

# Telegram Bot
app_bot = Application.builder().token(Config.BOT_TOKEN).build()

# ---------- BOT HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Signal Bot 🚀\nUse /subscribe to get premium access.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    order = razorpay_client.order.create({
        "amount": 10000,  # ₹100
        "currency": "INR",
        "payment_capture": "1"
    })

    payment_url = f"https://rzp.io/i/{order['id']}"
    await update.message.reply_text(f"Click here to pay: {payment_url}")

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("subscribe", subscribe))

# ---------- FLASK ROUTES ----------

@app.route("/")
def home():
    return "Signal Bot is Live 🚀"

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    return render_template("cancel.html")

@app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    data = request.json
    logger.info(f"Webhook data: {data}")
    return jsonify({"status": "ok"})

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    asyncio.run(app_bot.process_update(update))
    return "ok"

# ---------- RUN ----------

def run_flask():
    app.run(host="0.0.0.0", port=5000)

def run_bot():
    asyncio.run(app_bot.run_polling())

if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=run_bot).start()
