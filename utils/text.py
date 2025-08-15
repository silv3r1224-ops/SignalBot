def welcome_text():
    return (
        "👋 Welcome to *SignalBot*!\n\n"
        "I provide high-quality trading signals 📈.\n"
        "To access premium signals, please choose a subscription plan:\n\n"
        f"{plans_text()}\n"
        "Type /help to see available commands."
    )

def help_text():
    return (
        "🛠 *Help Menu*\n\n"
        "Available commands:\n"
        "/start - Start the bot & see plans\n"
        "/help - Show this help message\n"
        "/plans - Show subscription plans\n"
        "/pay <plan> - Pay for your subscription (bronze/silver/gold)\n"
        "/status - Check your subscription status\n"
        "/cancel - Cancel your subscription\n"
        "\nAdmin only:\n"
        "/broadcast all <message> - Send to all active subscribers\n"
        "/broadcast expired <message> - Send to expired subscribers"
    )

def plans_text():
    return (
        "💳 *Choose a plan:*\n"
        "• 🥉 Bronze – ₹199 / 30 days\n"
        "• 🥈 Silver – ₹499 / 90 days\n"
        "• 🥇 Gold – ₹1499 / 365 days\n\n"
        "Pay with `/pay <bronze|silver|gold>`"
    )

def payment_success_text(plan, expiry_date):
    return (
        f"✅ Payment successful!\n\n"
        f"Plan: *{plan.capitalize()}*\n"
        f"Valid until: {expiry_date}\n\n"
        "You will now start receiving premium signals 📢."
    )

def payment_failed_text():
    return (
        "❌ Payment failed or was cancelled.\n"
        "Please try again or contact support."
    )

def subscription_expired_text():
    return (
        "⚠️ Your subscription has expired.\n"
        f"{plans_text()}"
    )

def broadcast_usage_text():
    return (
        "⚠️ Usage:\n"
        "/broadcast all <message> - Send to all subscribers\n"
        "/broadcast expired <message> - Send to expired subscribers"
    )
