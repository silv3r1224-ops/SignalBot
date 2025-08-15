# bot.py
import hmac, hashlib, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
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

# Plan details
PLANS = {
    "Basic": 100,
    "Standard": 200,
    "Premium": 500
}

# Telegram commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for plan, amount in PLANS.items():
        keyboard.append([InlineKeyboardButton(f"{plan} - ₹{amount}", callback_data=f"pay_{plan}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a plan to pay:", reply_markup=reply_markup)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)
    await update.message.reply_text(f"Broadcasting: {message}")

# Handle plan selection
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_name = query.data.replace("pay_", "")
    amount = PLANS[plan_name] * 100  # Razorpay amount in paise

    # Create Razorpay payment link
    payment_link = razorpay_client.payment_link.create({
        "amount": amount,
        "currency": "INR",
        "description": f"{plan_name} plan subscription",
        "notes": {
            "telegram_id": str(query.from_user.id),
            "plan": plan_name
        },
        "customer": {
            "name": query.from_user.full_name,
            "email": "",  # optional
        },
        "notify": {
            "sms": True,
            "email": False
        },
        "callback_url": "https://signalbot-tfnb.onrender.com/razorpay-webhook",
        "callback_method": "get"
    })

    await query.edit_message_text(
        text=f"Click this link to pay for {plan_n_
