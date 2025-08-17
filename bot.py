import os
import logging
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import razorpay
from dotenv import load_dotenv

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not all([TELEGRAM_TOKEN, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, ADMIN_ID, WEBHOOK_SECRET]):
    raise RuntimeError("Some environment variables are missing!")

# --------------------------
# Logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------
# Razorpay client
# --------------------------
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# --------------------------
# Flask app for webhook
# --------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot & Server Running!"

@app.route('/razorpay-webhook', methods=['POST'])
def razorpay_webhook():
    try:
        signature = request.headers.get("X-Razorpay-Signature")
        payload = request.get_data(as_text=True)

        # Verify webhook
        razorpay_client.utility.verify_webhook_signature(payload, signature, WEBHOOK_SECRET)
        data = request.json
        logger.info(f"Verified webhook received: {data}")

        # Notify admin about successful payment
        asyncio.create_task(notify_admin(f"Payment successful: {data}"))

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        return jsonify({"status": "error"}), 400

# --------------------------
# Telegram bot setup
# --------------------------
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is running ✅")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

async def notify_admin(message: str):
    try:
        await telegram_app.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logger.error(f"Admin notification failed: {e}")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = 10000  # default ₹100
        if context.args:
            amount = int(float(context.args[0]) * 100)

        # Create Razorpay order
        order_data = {
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {"user": str(update.effective_user.id)}
        }
        order = razorpay_client.order.create(data=order_data)

        # Razorpay checkout link
        checkout_url = f"https://checkout.razorpay.com/v1/checkout.js?order_id={order['id']}"
        button = InlineKeyboardButton(text=f"Pay ₹{amount/100:.2f}", url=checkout_url)
        markup = InlineKeyboardMarkup([[button]])

        await update.message.reply_text("Click below to pay securely:", reply_markup=markup)
        await notify_admin(f"New payment order:\nUser: {update.effective_user.username}\nAmount: ₹{amount/100:.2f}\nOrder ID: {order['id']}")

    except Exception as e:
        logger.error(f"/pay error: {e}")
        await update.message.reply_text("Something went wrong while creating the payment.")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("pay", pay))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --------------------------
# Run bot in async loop
# --------------------------
async def main():
    await telegram_app.initialize()
    await telegram_app.start()
    logger.info("Telegram bot started")

    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    await serve(app, config)

    await telegram_app.stop()
    await telegram_app.shutdown()

# --------------------------
# Start
# --------------------------
if __name__ == "__main__":
    asyncio.run(main())
