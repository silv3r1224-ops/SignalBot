import razorpay
import config

PLANS = {
    "Basic": 99,
    "Pro": 199,
    "Premium": 499
}

razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

def create_payment_link(plan_name, user):
    amount = PLANS[plan_name] * 100  # paise
    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "telegram_id": str(user.id),
            "plan": plan_name
        }
    })
    return f"https://rzp.io/i/{order['id']}"
