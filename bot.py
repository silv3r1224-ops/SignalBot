from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from db import Base, engine, SessionLocal
from models import User
import config
from utils.text import plans_text

# Create tables
Base.metadata.create_all(bind=engine)

# Plan payment links
plans = {
    "Basic": "https://yourpaymentlink.com/basic",
    "Pro": "https://yourpaymentlink.com/pro",
    "Premium": "https://yourpaymentlink.com/premium"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(plan, callback_data=plan)] for plan in plans]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a plan to subscribe:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data

    # Add/update user in DB
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if not user:
        user = User(telegram_id=str(query.from_user.id), plan=plan)
        db.add(user)
    else:
        user.plan = plan
    db.commit()
    db.close()

    await query.edit_message_text(
        f"You selected: {plan}\nNow, use /pay to complete your payment."
    )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=str(update.effective_user.id)).first()
    db.close()

    if not user or not user.plan:
        await update.message.reply_text("Please select a plan first using /subscribe.")
        return

    payment_link = plans[user.plan]
    await update.message.reply_text(f"Click this link to pay for {user.plan}: {payment_link}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)

    db = SessionLocal()
    users = db.query(User).all()
    for u in users:
        try:
            await context.bot.send_message(chat_id=int(u.telegram_id), text=message)
        except Exception:
            continue
    db.close()
    await update.message.reply_text(f"Broadcast sent to {len(users)} users!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button))

    print("SignalBot is running...")
    app.run_polling()
