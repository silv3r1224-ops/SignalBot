import razorpay
import config

PLANS = {
    "Basic": 100,
    "Premium": 500,
    "VIP": 1000
}

razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

def create_payment_link(plan, user):
    amount = PLANS[plan] * 100  # in paise
    payment = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "telegram_id": user.id,
            "plan": plan
        }
    })
    return f"https://rzp.io/i/{payment['id']}"
