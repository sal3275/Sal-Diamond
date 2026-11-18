# Telegram Top-Up Bot V1

A beginner-friendly Telegram game top-up bot for:
- Free Fire
- Mobile Legends
- Honor of Kings
- Roblox
- Telegram Premium

Workflow:
Customer -> Choose product -> Enter ID -> Confirm -> See KHQR -> Upload payment screenshot -> Admin verifies -> Manual SEAGM top-up -> Complete order.

## 1. Install Python

Install Python 3.10+.

## 2. Create a virtual environment

macOS/Linux:
python3 -m venv venv
source venv/bin/activate

Windows:
python -m venv venv
venv\Scripts\activate

## 3. Install packages

pip install -r requirements.txt

## 4. Create your Telegram bot

Open Telegram and contact @BotFather.
Use /newbot and copy the bot token.

## 5. Find your Telegram Admin ID

You can use a trusted Telegram ID bot to find your numeric user ID.
Put the number in .env.

## 6. Configure .env

Copy .env.example to .env:

BOT_TOKEN=your_bot_token
ADMIN_ID=your_numeric_telegram_id
KHQR_IMAGE=payments/khqr.png

## 7. Add your KHQR

Put your KHQR image here:

payments/khqr.png

## 8. Run the bot

python bot.py

## IMPORTANT

The prices in bot.py are example prices. Replace them with your real SEAGM Member cost and selling prices.

Do not put your bot token in public GitHub repositories or share it with anyone.

This version uses manual payment verification and manual top-up through SEAGM.
