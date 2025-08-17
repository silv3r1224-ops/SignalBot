import os
import logging
import hmac
import hashlib
import asyncio
from dotenv import load_dotenv

from quart import Quart, request, jsonify
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import razorpay

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PORT = int(os.environ.get("PORT", 5000))
BASE_URL = os.environ.get("BASE_URL")  # e.g., https://signalbot-tfnb.onrender.com

if not all([TELEGRAM_TOKEN, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, WEBHOOK_SECRET, ADMIN_ID, BASE_URL]):
    raise RuntimeError("Missing one or more environment variables!")

# --------------------------
# Logging setup
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------
# Quart App
# --------------------------
app = Quart(__name__)

@app.route('/')
async def home():
    logger.info("Home route accessed")
    return "Bot & Server Running!"

@app.route('/razorpay-webhook', methods=['POST'])
async def razorpay_webhook():
    data = await request.data
    signature = request.headers.get('X-Razorpay-Signature')
    try:
        computed_hmac = hmac.new(bytes(WEBHOOK_SECRET, 'utf-8'), msg=data, digestmod=hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hmac, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({"status": "invalid signature"}), 400

        payload = await request.get_json()
        logger.info(f"Webhook received: {payload}")

        if payload.get("event") == "payment.captured":
            payment = payload['payload']['payment']['entity']
            order_id = payment['order_id']
            amount = payment['amount'] / 100
            user_id = payment.get('notes', {}).get('user_id')

            if user_id:
                await telegram_app.bot.send_message(chat_id=int(user_id), text=f"✅ Payment of ₹{amount} received!")

            await telegram_app.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💰 Payment captured!\nOrder ID: {order_id}\nAmount: ₹{amount}\nUser ID: {user_id}"
            )

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# --------------------------
# Razorpay client
# --------------------------
razor_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# --------------------------
# Telegram Bot
# --------------------------
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is running ✅")
    logger.info(f"/start used by {update.effective_user.username}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")
    logger.info(f"Message from {update.effective_user.username}: {update.message.text}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /pay <amount_in_rupees> <description>")
        return
    try:
        amount = int(float(context.args[0]) * 100)
        description = " ".join(context.args[1:])
        order = razor_client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{user_id}",
            "payment_capture": 1,
            "notes": {"user_id": str(user_id)}
        })
        payment_url = f"https://checkout.razorpay.com/v1/checkout.js?order_id={order['id']}"
        await update.message.reply_text(
            f"Payment order created!\nAmount: ₹{amount/100}\nDescription: {description}\nPay Now: {payment_url}"
        )
        logger.info(f"Payment created for {user_id}: {order}")
    except Exception as e:
        await update.message.reply_text(f"Error creating payment: {e}")
        logger.error(f"/pay error: {e}")

# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("pay", pay))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Telegram webhook route
# --------------------------
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
async def telegram_webhook():
    update = Update.de_json(await request.get_json(), telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return "ok", 200

# --------------------------
# Main asyncio loop
# --------------------------
async def main():
    # Initialize bot (do NOT start polling)
    await telegram_app.initialize()

    # Set webhook
    webhook_url = f"{BASE_URL}/{TELEGRAM_TOKEN}"
    await telegram_app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

    # Start Quart server
    await app.run_task(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())
