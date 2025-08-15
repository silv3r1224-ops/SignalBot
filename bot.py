import os
from flask import Flask
from threading import Thread
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from config import BOT_TOKEN, ADMIN_ID
from utils.text import plans_text
from db import session, Subscriber

# -------------------- Flask Webserver --------------------
app = Flask(__name__)

@app.route("/")
def index():
    return "SignalBot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_flask).start()

# -------------------- Telegram Bot --------------------
bot = Bot(token=BOT_TOKEN)
updater = Updater(token=BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# /start command
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    update.message.reply_text(
        f"Hello! Welcome to SignalBot.\n\n{plans_text()}"
    )

# /subscribe command
def subscribe(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscriber = session.query(Subscriber).filter_by(telegram_id=chat_id).first()
    if not subscriber:
        subscriber = Subscriber(telegram_id=chat_id)
        session.add(subscriber)
        session.commit()
    update.message.reply_text("You are now subscribed! Use /plans to view subscription plans.")

# /plans command
def plans(update: Update, context: CallbackContext):
    update.message.reply_text(plans_text())

# Admin broadcast command: /broadcast <message>
def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("Unauthorized.")
        return
    msg = " ".join(context.args)
    subscribers = session.query(Subscriber).all()
    for sub in subscribers:
        try:
            bot.send_message(chat_id=sub.telegram_id, text=msg)
        except:
            continue
    update.message.reply_text("Broadcast sent!")

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("subscribe", subscribe))
dispatcher.add_handler(CommandHandler("plans", plans))
dispatcher.add_handler(CommandHandler("broadcast", broadcast, pass_args=True))

# Start polling
updater.start_polling()
print("SignalBot started polling...")
updater.idle()
