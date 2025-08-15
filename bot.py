from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import config
from utils.text import plans_text

# Define your plans and payment links
plans = {
    "Basic": "https://yourpaymentlink.com/basic",
    "Pro": "https://yourpaymentlink.com/pro",
    "Premium": "https://yourpaymentlink.com/premium"
}

# Store user-selected plans temporarily
user_selected_plan = {}

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
    user_selected_plan[query.from_user.id] = plan
    await query.edit_message_text(
        f"You selected: {plan}\nNow, use /pay to complete your payment."
    )

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_selected_plan:
        await update.message.reply_text("Please select a plan first using /subscribe.")
        return
    plan = user_selected_plan[user_id]
    payment_link = plans[plan]
    await update.message.reply_text(f"Click this link to pay for {plan}: {payment_link}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)
    await update.message.reply_text(f"Broadcasting: {message}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(button))

    print("SignalBot is running...")
    app.run_polling()
