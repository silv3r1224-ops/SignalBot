import asyncio
import logging
import razorpay
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)

from config import BOT_TOKEN, ADMIN_ID, PLANS, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, payments_enabled
from db import init_db, upsert_user, is_banned, get_active_until, activate_subscription, create_payment, mark_payment_paid, iter_all_user_chat_ids, set_banned, stats
from utils.text import plans_text

# ---------------- Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("signalbot")

# ---------------- Razorpay client
rz_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if payments_enabled() else None

# ---------------- Handlers
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, update.effective_chat.id)
    if is_banned(u.id):
        await update.message.reply_text("🚫 You are banned.")
        return

    until = get_active_until(u.id)
    if until and until > datetime.utcnow():
        left_days = (until - datetime.utcnow()).days
        await update.message.reply_text(
            f"👋 Hi {u.first_name or 'there'}!\n"
            f"✅ Subscription active. Expires on {until.date()} ({left_days} day(s) left).\n\n"
            "Use /pay <plan> to extend."
        )
    else:
        await update.message.reply_text(
            "👋 Welcome to the Premium Signals Bot.\n\n"
            + plans_text()
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 Commands:\n"
        "/start – welcome/status\n"
        "/subscribe – view plans\n"
        "/pay <plan> – create payment link\n"
        "/verify – check your last payment link\n"
        "/status – subscription status\n\n"
        "Admin:\n"
        "/broadcast <message>\n/ban <user_id>\n/unban <user_id>\n/stats"
    )

async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🥉 Bronze – ₹199 / 30d", callback_data="plan:bronze")],
        [InlineKeyboardButton("🥈 Silver – ₹499 / 90d", callback_data="plan:silver")],
        [InlineKeyboardButton("🥇 Gold – ₹1499 / 365d", callback_data="plan:gold")],
    ]
    await update.message.reply_text(plans_text(), reply_markup=InlineKeyboardMarkup(kb))

async def plan_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, plan_key = q.data.split(":")
    await q.edit_message_text(
        f"Selected: {PLANS[plan_key]['name']} – ₹{PLANS[plan_key]['price_inr']}\n"
        f"Now type: /pay {plan_key}"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    until = get_active_until(u.id)
    if until and until > datetime.utcnow():
        left = until - datetime.utcnow()
        await update.message.reply_text(f"✅ Active. Expires on {until.date()} ({left.days} day(s) left).")
    else:
        await update.message.reply_text("❌ Not active.\n" + plans_text())

def _payment_notes(user: Update.effective_user.__class__, plan_key: str):
    return {"tg_user_id": str(user.id), "plan": plan_key, "source": "signalbot"}

async def pay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not payments_enabled():
        await update.message.reply_text("⚠️ Payments not configured. Contact admin.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /pay <bronze|silver|gold>")
        return
    plan_key = context.args[0].lower()
    if plan_key not in PLANS:
        await update.message.reply_text("Invalid plan. Use: bronze, silver, or gold.")
        return

    user = update.effective_user
    plan = PLANS[plan_key]
    amount_inr = plan["price_inr"]
    amount_paise = amount_inr * 100
    notes = _payment_notes(user, plan_key)

    try:
        pl = rz_client.payment_link.create({
            "amount": amount_paise,
            "currency": "INR",
            "description": f"{plan['name']} plan for @{user.username or user.id}",
            "notify": {"sms": False, "email": False},
            "notes": notes,
            "reminder_enable": True,
            "callback_url": "https://telegram.org",  # placeholder
            "callback_method": "get"
        })
        create_payment(user.id, plan_key, amount_inr, link_id=pl["id"], short_url=pl["short_url"])

        kb = [[InlineKeyboardButton("✅ I have paid", callback_data=f"verify:{pl['id']}")]]
        await update.message.reply_text(
            f"🧾 Payment Link created for *{plan['name']}* (₹{amount_inr}).\n\n"
            f"👉 Pay here: {pl['short_url']}\n\n"
            "After completing payment, tap **I have paid** to verify.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"Payment link error:\n`{e}`", parse_mode=ParseMode.MARKDOWN)

async def verify_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Checks latest link for the user by asking Razorpay if it's paid.
    # Simpler UX is via the button; this is a backup text command.
    await update.message.reply_text("Tap the 'I have paid' button on your last payment message, or pay again via /pay <plan>.")

async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, link_id = q.data.split(":", 1)
    try:
        link = rz_client.payment_link.fetch(link_id)
        status = link.get("status")  # created / sent / paid / cancelled
        payment_id = None
        if status == "paid":
            # pull payment id if present
            payments = link.get("payments", [])
            if payments and isinstance(payments, list):
                payment_id = payments[0].get("id")

            rec = mark_payment_paid(link_id, payment_id)
            if rec:
                activate_subscription(rec.user_id, rec.plan_key)
            await q.edit_message_text("✅ Payment verified! Your subscription is now active.\nUse /status to confirm.")
        else:
            await q.edit_message_text(f"❌ Not paid yet (status: {status}). If you already paid, wait ~30s and tap again.")
    except Exception as e:
        await q.edit_message_text(f"Verification failed:\n`{e}`", parse_mode=ParseMode.MARKDOWN)

# ---------------- Admin
def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    text = update.message.text.partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    sent, failed = 0, 0
    for chat_id in iter_all_user_chat_ids():
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
            await asyncio.sleep(0.02)  # be gentle
        except Exception:
            failed += 1
    await update.message.reply_text(f"📣 Broadcast done. Sent: {sent}, Failed: {failed}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    uid = int(context.args[0])
    set_banned(uid, True)
    await update.message.reply_text(f"User {uid} banned.")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    uid = int(context.args[0])
    set_banned(uid, False)
    await update.message.reply_text(f"User {uid} unbanned.")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    s = stats()
    await update.message.reply_text(f"📊 Stats\nUsers: {s['users']}\nActive Subs: {s['active_subscriptions']}\nPayments: {s['payments']}")

# ---------------- Bootstrap
async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing.")
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CallbackQueryHandler(plan_pick, pattern=r"^plan:"))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("pay", pay_cmd))
    app.add_handler(CommandHandler("verify", verify_cmd))
    app.add_handler(CallbackQueryHandler(verify_button, pattern=r"^verify:"))

    # Admin
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    log.info("Starting bot (long polling)…")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
