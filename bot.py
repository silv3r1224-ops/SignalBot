from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from utils.text import plans_text
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! " + plans_text())

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Select a plan to subscribe:\n" + plans_text())

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    message = " ".join(context.args)
    # For simplicity, broadcasting logic is not implemented here
    await update.message.reply_text(f"Broadcasting: {message}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("SignalBot is running...")
    app.run_polling()
