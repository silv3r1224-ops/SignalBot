import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import razorpay
import hmac, hashlib
import config

# Logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)

# Telegram bot
application = Application.builder().token(config.BOT_TOKEN).build()

# SQLAlchemy setup
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(String, unique=True)
    name = Column(String)

Base.metadata.create_all(engine)

# Razorpay client
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

# --- Telegram Handlers ---
async def start(update: Update, context):
    session = Session()
    tg_id = str(update.effective_user.id)
    user = session.query(User).filter_by(tg_id=tg_id).first()
    if not user:
        user = User(tg_id=tg_id, name=update.effective_user.full_name)
        session.add(user)
        session.commit()
    await update.message.reply_text("Welcome! You’re registered ✅")
    session.close()

async def echo(update: Update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --- Flask Routes ---
@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

@app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    expected_signature = hmac.new(
        config.RAZORPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        return "Invalid signature", 400

    data = request.json
    logging.info(f"Razorpay event: {data}")
    return jsonify({"status": "success"}), 200

# --- Startup ---
if __name__ == "__main__":
    webhook_url = f"{config.PUBLIC_URL}/telegram-webhook"
    application.run_webhook(
        listen="0.0.0.0",
        port=10000,
        url_path="telegram-webhook",
        webhook_url=webhook_url
    )
    app.run(host="0.0.0.0", port=5000)
