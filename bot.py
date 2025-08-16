import os
import logging
import razorpay
from flask import Flask, request, jsonify
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- Config ----------------
ADMIN_ID = 7909563220
BOT_TOKEN = "8250035384:AAHbSjhqT0fODfQHnjgBFcZLuIQeaUBJeP8"
RAZORPAY_KEY_ID = "rzp_test_R5a8j8yy3WEssP"
RAZORPAY_KEY_SECRET = "DNSIjreZrmVcqsP0n6goeAoq"
RAZORPAY_WEBHOOK_SECRET = "#Tesan25"

# ---------------- Telegram Bot ----------------
app_bot = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Bot is working ✅")

app_bot.add_handler(CommandHandler("start", start))

# ---------------- Flask ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot and Server are running!"

@app.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    data = request.json
    logging.info(f"Received webhook: {data}")
    return jsonify({"status": "success"}), 200

# ---------------- Run Functions ----------------
def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    # Start Flask in a background thread
    Thread(target=run_flask, daemon=True).start()

    # Run Telegram Bot in main thread (no event loop error)
    app_bot.run_polling()
