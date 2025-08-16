# utils/payments.py
import razorpay
import config

PLANS = {
    "Basic": 100,
    "Premium": 300,
    "VIP": 500
}

razorpay_client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

def create_payment_link(plan_name, user):
    amount = PLANS.get(plan_name, 0) * 100  # in paise
    payment = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "notes": {"telegram_id": str(user.id), "plan": plan_name}
    })
    return f"https://rzp.io/i/{payment['id']}"  # example link
