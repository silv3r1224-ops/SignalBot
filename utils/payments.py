# utils/payments.py
import razorpay
import config

client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

PLANS = {
    "Basic": 100,
    "Standard": 200,
    "Premium": 500
}

def create_payment_link(plan_name, telegram_user):
    amount = PLANS[plan_name] * 100  # paise
    payment_link = client.payment_link.create({
        "amount": amount,
        "currency": "INR",
        "description": f"{plan_name} plan subscription",
        "notes": {
            "telegram_id": str(telegram_user.id),
            "plan": plan_name
        },
        "customer": {
            "name": telegram_user.full_name,
        },
        "notify": {
            "sms": True,
            "email": False
        },
        "callback_url": "https://signalbot-tfnb.onrender.com/razorpay-webhook",
        "callback_method": "get"
    })
    return payment_link['short_url']
