import razorpay
import config

client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

def create_payment_link(plan_name, user_email=None, user_phone=None):
    amount = config.PLANS.get(plan_name.lower())
    if not amount:
        return None

    data = {
        "amount": amount,
        "currency": "INR",
        "accept_partial": False,  # set True if you want partial payment
        "description": f"{plan_name.capitalize()} Plan Subscription",
        "customer": {
            "email": user_email or "example@example.com",
            "contact": user_phone or "9999999999"
        },
        "notify": {
            "sms": True,
            "email": True
        },
        "reminder_enable": True
    }

    response = client.payment_link.create(data)
    return response.get("short_url")
