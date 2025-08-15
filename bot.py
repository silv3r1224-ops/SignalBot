import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import BOT_TOKEN, ADMIN_ID
from utils.text import plans_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Signal Bot!\nUse /plans to view subscription options.")

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(plans_text())

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("Unauthorized")
    msg = " ".join(context.args)
    if not msg:
        return await update.message.reply_text("Usage: /broadcast <message>")
    # Here you can loop through subscribers and send them the msg
    await update.message.reply_text(f"Broadcast sent: {msg}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("plans", plans))
    app.add_handler(CommandHandler("broadcast", broadcast))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
