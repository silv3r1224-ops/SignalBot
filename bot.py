from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from utils.text import plans_text
from utils import payments
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /pay <plan_name>\n" + plans_text())
        return

    plan_name = context.args[0].lower()
    payment_link = payments.create_payment_link(plan_name, 
                                                user_email="customer@example.com", 
                                                user_phone="9876543210")
    if payment_link:
        await update.message.reply_text(f"Click this link to pay for {plan_name.capitalize()}: {payment_link}")
    else:
        await update.message.reply_text("Invalid plan. Choose from:\n" + plans_text())

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", subscribe))

    print("SignalBot is running...")
    app.run_polling()
