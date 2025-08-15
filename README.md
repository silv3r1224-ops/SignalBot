# Telegram Signal Bot (Render, Polling Only)

## Features
- Long-polling Telegram bot (no webhooks)
- Razorpay Payment Links (create + verify on demand)
- Subscriptions with stacking durations (SQLite + SQLAlchemy)
- Admin tools: broadcast, ban/unban, stats

## Render Setup
- Build: `pip install -r requirements.txt`
- Start: `python bot.py`
- Env:
  - BOT_TOKEN
  - ADMIN_ID
  - RAZORPAY_KEY_ID
  - RAZORPAY_KEY_SECRET
  - DATABASE_URL (optional; defaults to sqlite)

## Commands
- `/start`, `/help`, `/subscribe`, `/status`
- `/pay <bronze|silver|gold>`
- Tap **I have paid** to verify, or `/verify`
- Admin: `/broadcast <msg>`, `/ban <user_id>`, `/unban <user_id>`, `/stats`
