import json
import asyncio
from flask import Flask, request
import hmac, hashlib
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import razorpay
from datetime import datetime, timedelta
import threading

# ---------------- CONFIG ----------------
TELEGRAM_TOKEN = "8250035384:AAHbSjhqT0fODfQHnjgBFcZLuIQeaUBJeP8"
RAZORPAY_KEY_ID = "rzp_test_R5a8j8yy3WEssP"
RAZORPAY_KEY_SECRET = "DNSIjreZrmVcqsP0n6goeAoq"
ADMIN_ID = 123456789  # Replace with your Telegram ID

SUBSCRIBERS_FILE = "subscribers.json"
PLANS_FILE = "plans.json"
# ----------------------------------------

# Load subscribers
try:
    with open(SUBSCRIBERS_FILE, "r") as f:
        subscribers = json.load(f)
except FileNotFoundError:
    subscribers = {}

def save_subscribers():
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subscribers, f)

# Load subscription plans
try:
    with open(PLANS_FILE, "r") as f:
        plans = json.load(f)
except FileNotFoundError:
    plans = {
        "basic": {"price": 10000, "duration_days": 7},  # ₹100, 7 days
        "premium": {"price": 25000, "duration_days": 30} # ₹250, 30 days
    }
    with open(PLANS_FILE, "w") as f:
        json.dump(plans, f)

# Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Flask app for webhook
app = Flask(__name__)

@app.route("/razorpay_webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    secret = RAZORPAY_KEY_SECRET.encode()
    generated_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    if hmac.compare_digest(signature, generated_signature):
        data = request.json
        if data.get("event") == "payment.captured":
            user_id = str(data["payload"]["payment"]["entity"]["notes"]["telegram_id"])
            plan = data["payload"]["payment"]["entity"]["notes"].get("plan", "basic")
            duration = plans.get(plan, plans["basic"])["duration_days"]
            expiry = datetime.now() + timedelta(days=duration)
            subscribers[user_id] = expiry.strftime("%Y-%m-%d %H:%M:%S")
            save_subscribers()
            asyncio.run(send_welcome(user_id, plan))
        return "", 200
    return "Invalid signature", 400

async def send_welcome(user_id, plan):
    await telegram_app.bot.send_message(
        chat_id=int(user_id),
        text=f"✅ Payment received! You are subscribed to {plan} plan until {subscribers[user_id]}"
    )

# ---------------- TELEGRAM BOT ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! To subscribe to trading signals, use /subscribe <plan>\nAvailable plans: basic, premium"
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if len(context.args) < 1 or context.args[0] not in plans:
        await update.message.reply_text("❌ Invalid plan. Available: basic, premium")
        return

    plan = context.args[0]
    amount = plans[plan]["price"]
    payment = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1",
        "notes": {"telegram_id": user_id, "plan": plan}
    })
    payment_url = f"https://checkout.razorpay.com/v1/checkout.js?order_id={payment['id']}"
    await update.message.reply_text(
        f"Click the link to pay ₹{amount/100:.2f} for {plan} plan: {payment_url}"
    )

async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized.")
        return
    message = " ".join(context.args)
    now = datetime.now()
    expired_users = []
    for user_id, expiry_str in subscribers.items():
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        if expiry >= now:
            await context.bot.send_message(chat_id=int(user_id), text=f"📈 Signal: {message}")
        else:
            expired_users.append(user_id)
    # Remove expired users
    for u in expired_users:
        subscribers.pop(u)
    save_subscribers()
    await update.message.reply_text("✅ Signal sent to active subscribers!")

# ---------------- RUN TELEGRAM ----------------
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("subscribe", subscribe))
telegram_app.add_handler(CommandHandler("send", send_signal))

def run_telegram():
    telegram_app.run_polling()

threading.Thread(target=run_telegram).start()

# ---------------- RUN FLASK ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
