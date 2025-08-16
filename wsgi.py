from flask import Flask, request, jsonify
import json
from bot import db, User, Payment, app_bot
import razorpay
import config
from threading import Thread

flask_app = Flask(__name__)

# Razorpay client
razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

@flask_app.route("/razorpay-webhook", methods=["POST"])
def razorpay_webhook():
    payload = request.data
    signature = request.headers.get("X-Razorpay-Signature")
    secret = config.RAZORPAY_WEBHOOK_SECRET

    # Verify webhook
    try:
        razorpay_client.utility.verify_webhook_signature(payload, signature, secret)
    except:
        return jsonify({"status": "invalid signature"}), 400

    data = json.loads(payload)
    payment_entity = data["payload"]["payment"]["entity"]
    payment_id = payment_entity["id"]
    amount = payment_entity["amount"] / 100
    status = payment_entity["status"]
    telegram_id = payment_entity["notes"].get("telegram_id")
    plan = payment_entity["notes"].get("plan", "")

    if telegram_id:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
        if not user:
            user = User(telegram_id=str(telegram_id))
            db.add(user)
            db.commit()
            db.refresh(user)
        user.subscribed = status == "captured"
        user.plan = plan
        db.add(user)
        db.commit()

        payment = Payment(user_id=user.id, razorpay_payment_id=payment_id, amount=amount, status=status)
        db.add(payment)
        db.commit()

        # Notify user on Telegram
        if status == "captured":
            try:
                Thread(target=lambda: app_bot.bot.send_message(
                    chat_id=int(telegram_id),
                    text=f"✅ Payment of ₹{amount} for {plan} plan successful! You are now subscribed."
                )).start()
            except:
                pass

    return jsonify({"status": "success"}), 200
