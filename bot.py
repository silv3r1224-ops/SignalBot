import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import razorpay
import hmac
import hashlib
from threading import Thread
import asyncio

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

if not all([TELEGRAM_TOKEN, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, WEBHOOK_SECRET, ADMIN_ID]):
    raise RuntimeError("One or more environment variables are missing!")

# --------------------------
# Logging setup
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------
# Flask setup
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Home route accessed")
    return "Bot & Server Running!"

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    data = request.data
    signature = request.headers.get('X-Razorpay-Signature')
    try:
        hmac_sha256 = hmac.new(
            bytes(WEBHOOK_SECRET, 'utf-8'),
            msg=data,
            digestmod=hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(hmac_sha256, signature):
            payload = request.json
            logger.info(f"Valid webhook received: {payload}")

            if payload.get("event") == "payment.captured":
                order_id = payload['payload']['payment']['entity']['order_id']
                amount = payload['payload']['payment']['entity']['amount'] / 100
                user_id = payload['payload']['payment']['entity'].get('notes', {}).get('user_id')

                # Notify user if user_id exists
                if user_id:
                    asyncio.create_task(
                        telegram_app.bot.send_message(
                            chat_id=int(user_id),
                            text=f"✅ Payment of ₹{amount} received successfully!"
                        )
                    )

                # Notify admin
                asyncio.create_task(
                    telegram_app.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"💰 Payment captured!\nOrder ID: {order_id}\nAmount: ₹{amount}\nUser ID: {user_id}"
                    )
                )

            return jsonify({"status": "ok"}), 200
        else:
            logger.warning("Invalid webhook signature")
            return jsonify({"status": "invalid signature"}), 400
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# --------------------------
# Razorpay client
# --------------------------
razor_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# --------------------------
# Telegram Bot setup
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

        payment_url = f"https://rzp.io/i/{order['id']}"  # user-friendly link
        await update.message.reply_text(
            f"Payment order created!\nAmount: ₹{amount/100}\nDescription: {description}\nPay Now: {payment_url}"
        )
        logger.info(f"Payment created for {user_id}: {order}")
    except Exception as e:
        await update.message.reply_text(f"Error creating payment: {e}")
        logger.error(f"Error in /pay: {e}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
telegram_app.add_handler(CommandHandler("pay", pay))

# --------------------------
# Run Telegram bot in thread
# --------------------------
def run_bot():
    telegram_app.run_polling()

bot_thread = Thread(target=run_bot, daemon=True)
bot_thread.start()

# --------------------------
# Run Flask normally
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
