import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Parse Admin IDs safely
admin_raw = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "0"))
ADMIN_IDS = [int(x.strip()) for x in admin_raw.split(",") if x.strip().replace("-", "").isdigit()]

def parse_env_int(var_name, default_val):
    val = os.getenv(var_name, str(default_val))
    if "=" in val:
        val = val.split("=")[-1]
    try:
        return int(val.strip())
    except ValueError:
        return default_val

GROUP_ID = parse_env_int("GROUP_ID", -1003957662857)
GROUP_2_ID = parse_env_int("GROUP_2_ID", 0)

KHQR_IMAGE = os.getenv("KHQR_IMAGE", "payments/khqr.png")
LOGO_IMAGE = os.getenv("LOGO_IMAGE", "logo.png")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "orders.db")

PRODUCTS = {
    "free_fire": {
        "name": "🔥 Free Fire",
        "packages": [
            ("💎 100 Diamonds", 1.00, 1.20),
            ("💎 210 Diamonds", 2.00, 2.40),
            ("💎 530 Diamonds", 4.80, 5.50),
            ("💎 1080 Diamonds", 9.50, 10.80),
            ("💎 2200 Diamonds", 19.00, 21.50),
            ("🎟️ Weekly Pass", 1.80, 2.20),
            ("🎫 Monthly Pass", 8.50, 10.00),
        ],
    },
    "mobile_legends": {
        "name": "💎 Mobile Legends",
        "packages": [
            ("💎 14 Diamonds", 0.25, 0.35),
            ("💎 22 Diamonds", 0.35, 0.45),
            ("💎 56 Diamonds", 0.90, 1.10),
            ("💎 86 Diamonds", 1.35, 1.65),
            ("💎 112 Diamonds", 1.70, 2.10),
            ("💎 172 Diamonds", 2.60, 3.20),
            ("💎 224 Diamonds", 3.50, 4.20),
            ("💎 336 Diamonds", 5.20, 6.20),
            ("🎟️ Weekly Diamond Pass", 1.60, 1.99),
            ("🎫 Twilight Pass", 8.20, 9.80),
        ],
    },
    "Honor of Kings": {
        "name": "👑 Honor of Kings",
        "packages": [
            ("🪙 16 Tokens", 0.22, 0.30),
            ("🪙 80+8 Tokens", 1.00, 1.25),
            ("🪙 240+17 Tokens", 2.90, 3.50),
            ("🪙 400+32 Tokens", 4.80, 5.80),
            ("🪙 560+45 Tokens", 6.50, 7.90),
            ("🪙 800+95 Tokens", 9.20, 11.00),
            ("🪙 1200+150 Tokens", 14.00, 16.50),
            ("🪙 2400+320 Tokens", 27.00, 32.00),
            ("🎫 Weekly Card", 0.95, 1.20),
            ("🎫 Weekly Card Plus", 2.70, 3.30),
        ],
    },
    "telegram_premium": {
        "name": "⭐ Telegram Premium",
        "packages": [
            ("⭐ 3 Months Premium", 11.50, 13.80),
            ("⭐ 6 Months Premium", 15.00, 18.50),
            ("⭐ 12 Months Premium", 28.00, 33.50),
        ],
    },
}

WAITING_PLAYER_ID, WAITING_PAYMENT, WAITING_SUPPORT_MSG = range(3)

def safe_caption(text: str, limit: int = 1000) -> str:
    """Ensure captions never exceed Telegram's limit of 1024 characters."""
    if len(text) > limit:
        return text[:limit] + "..."
    return text

def db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            game_key TEXT NOT NULL,
            game_name TEXT NOT NULL,
            package_name TEXT NOT NULL,
            player_id TEXT NOT NULL,
            cost REAL NOT NULL,
            selling_price REAL NOT NULL,
            profit REAL NOT NULL,
            status TEXT NOT NULL,
            payment_file_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def generate_order_receipt(order):
    status_map = {
        "PAYMENT_REVIEW": "⏳ PENDING REVIEW",
        "PAID_VERIFIED": "✅ PAID & VERIFIED", 
        "TOPUP_PROCESSING": "🚀 PROCESSING",
        "COMPLETED": "🎉 COMPLETED",
        "PAYMENT_REJECTED": "❌ REJECTED"
    }
    status_display = status_map.get(order["status"], f"⏳ {order['status']}")
    username_display = f"@{order['username']}" if order['username'] else "No username"

    try:
        dt = datetime.fromisoformat(order["created_at"])
        formatted_date = dt.strftime("%d-%m-%Y %I:%M:%S %p")
    except Exception:
        formatted_date = order["created_at"]

    return (
        "🧾 **SAL DIAMOND OFFICIAL RECEIPT**\n"
        "=============================\n"
        f"🆔 **ORDER ID :** `#{order['id']}`\n"
        f"👤 **CUSTOMER :** {username_display}\n"
        f"🎮 **GAME :** {order['game_name']}\n"
        f"📦 **PACKAGE :** {order['package_name']}\n"
        f"🎯 **PLAYER ID:** `{order['player_id']}`\n"
        f"💵 **TOTAL :** `${order['selling_price']:.2f}`\n"
        "-----------------------------\n"
        f"📌 **STATUS :** {status_display}\n"
        f"📅 **DATE :** `{formatted_date}`\n"
        "============================-\n"
        "🙏 **អរគុណច្រើនសម្រាប់ការប្រើប្រាស់សេវាកម្មរបស់យើងខ្ញុំ!**\n"
        "✨ *Thank you for choosing our service!*"
    )

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Free Fire", callback_data="game:free_fire")],
        [InlineKeyboardButton("💎 Mobile Legends", callback_data="game:mobile_legends")],
        [InlineKeyboardButton("👑 Honor of Kings", callback_data="game:Honor of Kings")],
        [InlineKeyboardButton("⭐ Telegram Premium", callback_data="game:telegram_premium")],
        [InlineKeyboardButton("🛒 ការបញ្ជាទិញរបស់ខ្ញុំ", callback_data="my_orders")],
        [InlineKeyboardButton("💬 ជំនួយ / Contact Support", callback_data="support_menu")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption_text = (
        "🎮 *ស្វាគមន៍មកកាន់ SAL DIAMOND TOP UP!*\n\n"
        "⚡ រហ័ស • សុវត្ថិភាព • តម្លៃសមរម្យ\n\n"
        "សូមជ្រើសរើសសេវាកម្មខាងក្រោម៖"
    )

    if os.path.exists(LOGO_IMAGE):
        with open(LOGO_IMAGE, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=safe_caption(caption_text), reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(caption_text, reply_markup=main_menu(), parse_mode="Markdown")

async def choose_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game_key = query.data.split(":")[1]
    context.user_data["game_key"] = game_key

    product = PRODUCTS[game_key]
    buttons = []

    for i, (package, cost, price) in enumerate(product["packages"]):
        buttons.append([InlineKeyboardButton(f"{package} — ${price:.2f}", callback_data=f"pkg:{game_key}:{i}")])

    buttons.append([InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="back")])
    text_content = f"*{product['name']}*\n\nសូមជ្រើសរើសកញ្ចប់៖"

    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(text_content), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await query.edit_message_text(text=text_content, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def choose_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, game_key, index = query.data.split(":")
    index = int(index)

    package, cost, price = PRODUCTS[game_key]["packages"][index]
    context.user_data["package"] = package
    context.user_data["cost"] = cost
    context.user_data["price"] = price

    await query.message.reply_text(
        f"🛒 បានជ្រើសរើស៖
