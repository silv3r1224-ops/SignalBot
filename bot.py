from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from utils.text import plans_text
from utils.payments import create_payment_link, PLANS
from db import SessionLocal, engine, Base
from models import User, Payment
import config
from threading import Thread
import asyncio

# Database setup
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Telegram bot
app_bot = ApplicationBuilder().token(config.BOT_TOKEN).build()

# Telegram Commands
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

# Handlers
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("subscribe", subscribe))
app_bot.add_handler(CommandHandler("broadcast", broadcast))
app_bot.add_handler(CallbackQueryHandler(button))

# Run bot in a separate thread (for polling)
def start_bot():
    asyncio.run(app_bot.run_polling())

Thread(target=start_bot, daemon=True).start()
