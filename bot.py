import os
import sqlite3
import re
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
    
    raw_user = order['username'] or "No username"
    safe_user = raw_user.replace("_", "\\_").replace("*", "\\*")
    username_display = f"@{safe_user}" if order['username'] else "No username"

    try:
        dt = datetime.fromisoformat(order["created_at"])
        formatted_date = dt.strftime("%d-%m-%Y %I:%M:%S %p")
    except Exception:
        formatted_date = order["created_at"]

    return (
        "🧾 *SAL DIAMOND OFFICIAL RECEIPT*\n"
        "=============================\n"
        f"🆔 *ORDER ID :* `#{order['id']}`\n"
        f"👤 *CUSTOMER :* {username_display}\n"
        f"🎮 *GAME :* {order['game_name']}\n"
        f"📦 *PACKAGE :* {order['package_name']}\n"
        f"🎯 *PLAYER ID:* `{order['player_id']}`\n"
        f"💵 *TOTAL :* `${order['selling_price']:.2f}`\n"
        "-----------------------------\n"
        f"📌 *STATUS :* {status_display}\n"
        f"📅 *DATE :* `{formatted_date}`\n"
        "=============================\n"
        "🙏 *អរគុណច្រើនសម្រាប់ការប្រើប្រាស់សេវាកម្មរបស់យើងខ្ញុំ!*\n"
        "✨ _Thank you for choosing our service!_"
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
        f"🛒 បានជ្រើសរើស៖ {package}\n"
        f"💵 តម្លៃ៖ ${price:.2f}\n\n"
        "សូមផ្ញើ Player ID / UID / Username របស់អ្នកមកទីនេះ៖"
    )
    return WAITING_PLAYER_ID

async def receive_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_id = update.message.text.strip()
    context.user_data["player_id"] = player_id

    game_key = context.user_data.get("game_key", "mobile_legends")
    game_name = PRODUCTS.get(game_key, {}).get("name", "Mobile Legends")
    package = context.user_data.get("package", "Diamonds")
    price = context.user_data.get("price", 0.0)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ បញ្ជាក់ការបញ្ជាទិញ", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_order")],
    ])

    await update.message.reply_text(
        f"🧾 *សេចក្តីសង្ខេបការបញ្ជាទិញ*\n\n"
        f"🎮 ហ្គេម៖ {game_name}\n"
        f"💎 កញ្ចប់៖ {package}\n"
        f"👤 ID អ្នកលេង៖ `{player_id}`\n"
        f"💵 តម្លៃសរុប៖ *${price:.2f}*\n\n"
        "សូមពិនិត្យ និងបញ្ជាក់ការបញ្ជាទិញរបស់អ្នក។",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    price = context.user_data.get("price", 0.0)
    caption_text = (
        "📸 ស្កេនបង់ប្រាក់ រួចផ្ញើ Receipt មកទីនេះ\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏛 KHQR ABA PAYMENT\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 អ្នកត្រូវបង់ប្រាក់: ${price:.2f}\n"
        f"Player / Username: {context.user_data.get('player_id', 'N/A')}\n"
        f"💵 ចំនួនទឹកប្រាក់: ${price:.2f}\n"
        "❗ សូមទំនាក់ទំនង Admin ប្រសិនបើមានបញ្ហា。\n"
        "❗ សូមចំណាំ៖ ប្រសិនបើចំនួនទឹកប្រាក់មិនត្រឹមត្រូវ ខាងយើងមិនដាក់ជូនទេ!"
    )

    await query.edit_message_text("💳 កំពុងបង្កើតព័ត៌មានបង់ប្រាក់...")

    if os.path.exists("khqr.png"):
        with open("khqr.png", "rb") as photo_file:
            await query.message.reply_photo(
                photo=photo_file,
                caption=caption_text,
                parse_mode="Markdown"
            )
    else:
        await query.message.reply_text(caption_text, parse_mode="Markdown")

    return WAITING_PAYMENT

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ ការបញ្ជាទិញត្រូវបានបោះបង់。")
    return ConversationHandler.END

async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📸 សូមផ្ញើរូបថតអេក្រង់ (Receipt) នៃការបង់ប្រាក់。")
        return WAITING_PAYMENT

    photo = update.message.photo[-1]
    user = update.effective_user

    game_key = context.user_data.get("game_key", "mobile_legends")
    game_name = PRODUCTS.get(game_key, {}).get("name", "Mobile Legends")
    package = context.user_data.get("package", "Diamonds")
    player_id = context.user_data.get("player_id", "N/A")
    cost = context.user_data.get("cost", 0.0)
    price = context.user_data.get("price", 0.0)
    profit = price - cost

    conn = db()
    cur = conn.execute("""
        INSERT INTO orders
        (telegram_id, username, game_key, game_name, package_name,
         player_id, cost, selling_price, profit, status,
         payment_file_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user.id, user.username or "", game_key, game_name, package,
        player_id, cost, price, profit, "PAYMENT_REVIEW",
        photo.file_id, datetime.now().isoformat(timespec="seconds")
    ))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ ទទួលបានវិក្កយបត្របង់ប្រាក់ហើយ!\n\n"
        f"លេខអូឌើ (Order ID): #{order_id}\n"
        "⏳ ស្ថានភាព៖ កំពុងរង់ចាំការពិនិត្យផ្ទៀងផ្ទាត់..."
    )

    safe_username = (user.username or "No username").replace("_", "\\_").replace("*", "\\*")
    admin_text = (
        f"🔔 *ការបញ្ជាទិញថ្មី #{order_id}*\n\n"
        f"🎮 *ហ្គេម:* {game_name}\n"
        f"💎 *កញ្ចប់:* {package}\n"
        f"👤 *ID អ្នកលេង:* `{player_id}`\n"
        f"💵 *ប្រាក់អតិថិជនបង់:* ${price:.2f}\n"
        f"💰 *ប្រាក់ចំណេញ:* ${profit:.2f}\n"
        f"👤 *Telegram:* @{safe_username}\n\n"
        f"📌 *ស្ថានភាព:* ⏳ PENDING REVIEW"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ផ្ទៀងផ្ទាត់ការបង់ប្រាក់", callback_data=f"verify:{order_id}")],
        [InlineKeyboardButton("❌ បដិសេធការបង់ប្រាក់", callback_data=f"reject:{order_id}")],
    ])

    try:
        await context.bot.send_photo(
            chat_id=GROUP_ID, photo=photo.file_id,
            caption=safe_caption(admin_text), reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Error sending to group: {e}")

    return ConversationHandler.END

async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ FAQ / សំណួរញឹកញាប់", callback_data="support_faq")],
        [InlineKeyboardButton("📩 ផ្ញើសារទៅកាន់ Admin", callback_data="support_contact")],
        [InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="back")],
    ])
    text = "🎧 *មជ្ឈមណ្ឌលជំនួយ និងគាំទ្រ (Support Center)*\n\nសូមជ្រើសរើសជម្រើសខាងក្រោម៖"

    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(text), reply_markup=keyboard, parse_mode="Markdown")
    else:
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")

async def support_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    faq_text = (
        "<b>❓ សំណួរដែលសួរញឹកញាប់ (FAQ)</b>\n\n"
        "🔹 <b>តើ Top Up រយៈពេលប៉ុន្មានទើបចូល?</b>\n"
        "👉 បន្ទាប់ពីលោកអ្នកបង់ប្រាក់ ៥ ទៅ ១៥ នាទីបន្ទាប់ពីការបញ្ជាក់ជាក់ស្តែង。\n\n"
        "🔹 <b>តើធ្វើម៉េច Player ID ខុស?</b>\n"
        "👉 សូមប្រញាប់ចុច <b>«ធ្វើសេវាទៅសេវា Admin»</b> ដើម្បីកែប្រែភ្លាមៗ!\n\n"
        "🔹 <b>អត់បានទទួលប្រាក់ហើយ តែមិនដំណើរការ?</b>\n"
        "👉 សូមផ្ញើវិក្កយបត្រ (Receipt) ចូលមកកាន់ Admin តាមរយៈប៊ូតុងខាងក្រោម。"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 ធ្វើសេវាទៅសេវា Admin", callback_data="support_contact")],
        [InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="support_menu")],
    ])

    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(faq_text), reply_markup=keyboard, parse_mode="HTML")
    else:
        await query.edit_message_text(text=faq_text, reply_markup=keyboard, parse_mode="HTML")

async def start_support_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "📝 *ផ្ញើសារសាកសួរទៅកាន់ Admin*\n\nសូមសរសេរសារ ឬបញ្ហារបស់អ្នកមកទីនេះ៖"

    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(text), parse_mode="Markdown")
    else:
        await query.edit_message_text(text=text, parse_mode="Markdown")

    return WAITING_SUPPORT_MSG

async def receive_support_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    user_text = msg.text or msg.caption or "[Media Only]"

    safe_name = (user.full_name or "Unknown").replace("_", "\\_").replace("*", "\\*")
    safe_username = (user.username or "No username").replace("_", "\\_").replace("*", "\\*")

    ticket_info = (
        f"📩 *សារជំនួយថ្មី (Support Ticket)*\n\n"
        f"👤 *ពី:* {safe_name} (@{safe_username})\n"
        f"🆔 *User ID:* `{user.id}`\n\n"
        f"💬 *សារ:* {user_text}\n\n"
        f"👇 *របៀបឆ្លើយតប:* Reply សារនេះដើម្បីឆ្លើយតបទៅកាន់អតិថិជន。"
    )

    target_chat = GROUP_2_ID if GROUP_2_ID != 0 else GROUP_ID

    try:
        if msg.photo:
            await context.bot.send_photo(chat_id=target_chat, photo=msg.photo[-1].file_id, caption=safe_caption(ticket_info), parse_mode="Markdown")
        elif msg.document:
            await context.bot.send_document(chat_id=target_chat, document=msg.document.file_id, caption=safe_caption(ticket_info), parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=target_chat, text=ticket_info, parse_mode="Markdown")

        await msg.reply_text("✅ សាររបស់អ្នកត្រូវបានផ្ញើទៅកាន់ក្រុមការងារ Admin រួចរាល់ហើយ!")
    except Exception as e:
        print(f"Error sending support message: {e}")

    return ConversationHandler.END

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.reply_to_message:
        return

    valid_groups = [g for g in [GROUP_ID, GROUP_2_ID] if g != 0]
    if valid_groups and message.chat.id not in valid_groups:
        return

    replied_text = message.reply_to_message.caption or message.reply_to_message.text or ""
    if "User ID:" not in replied_text:
        return

    try:
        match = re.search(r"User ID:\D*(\d+)", replied_text)
        if not match:
            await message.reply_text("❌ រកមិនឃើញ User ID ក្នុងសារដែលได้ Reply ទេ។")
            return
            
        target_user_id = int(match.group(1))
        admin_reply_text = message.text or message.caption or ""

        if message.photo:
            await context.bot.send_photo(
                chat_id=target_user_id,
                photo=message.photo[-1].file_id,
                caption=f"💬 *សារឆ្លើយតបពី Admin៖*\n\n{admin_reply_text}",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"💬 *សារឆ្លើយតបពី Admin៖*\n\n{admin_reply_text}",
                parse_mode="Markdown"
            )

        await message.reply_text("✅ បានផ្ញើសារឆ្លើយតបទៅកាន់អតិថិជនជោគជ័យ!")
    except Exception as e:
        print(f"❌ Error replying to user: {e}")
        await message.reply_text(f"❌ មិនអាចផ្ញើសារទៅកាន់អតិថិជនបានទេ: {e}")

async def direct_support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private" and update.message and update.message.text and not update.message.text.startswith("/"):
        await receive_support_msg(update, context)

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    is_authorized = user_id in ADMIN_IDS
    if not is_authorized:
        for gid in [GROUP_ID, GROUP_2_ID]:
            if gid == 0: continue
            try:
                member = await context.bot.get_chat_member(gid, user_id)
                if member.status in ["administrator", "creator"]:
                    is_authorized = True
                    break
            except Exception:
                pass

    if not is_authorized:
        await query.answer("⚠️ អ្នកគ្មានសិទ្ធិគ្រប់គ្រងអូឌើទេ!", show_alert=True)
        return

    await query.answer()
    action, order_id = query.data.split(":")
    order_id = int(order_id)

    conn = db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()

    if not order:
        await query.edit_message_caption(
            caption=f"🔔 *ការបញ្ជាទិញ #{order_id}*\n\n📌 *ស្ថានភាព:* 🎉 COMPLETED\n*(ការបញ្ជាទិញបានបញ្ចប់រួចរាល់)*",
            parse_mode="Markdown"
        )
        conn.close()
        return

    safe_username = (order["username"] or "No username").replace("_", "\\_").replace("*", "\\*")
    
    status_text_map = {
        "PAYMENT_REVIEW": "⏳ PENDING REVIEW",
        "PAID_VERIFIED": "✅ PAID & VERIFIED",
        "TOPUP_PROCESSING": "🚀 TOP-UP PROCESSING",
        "COMPLETED": "🎉 COMPLETED",
        "PAYMENT_REJECTED": "❌ REJECTED"
    }

    base_admin_text = (
        f"🔔 *ការបញ្ជាទិញ #{order_id}*\n\n"
        f"🎮 *ហ្គេម:* {order['game_name']}\n"
        f"💎 *កញ្ចប់:* {order['package_name']}\n"
        f"👤 *ID អ្នកលេង:* `{order['player_id']}`\n"
        f"💵 *ប្រាក់អតិថិជនបង់:* ${order['selling_price']:.2f}\n"
        f"💰 *ប្រាក់ចំណេញ:* ${order['profit']:.2f}\n"
        f"👤 *Telegram:* @{safe_username}\n\n"
    )

    keyboard = None  # កំណត់តម្លៃមេ (Default) ទុកមុនដើម្បីការពារ UnboundLocalError

    if action == "verify":
        conn.execute("UPDATE orders SET status = 'PAID_VERIFIED' WHERE id = ?", (order_id,))
        conn.commit()
        updated_status = status_text_map["PAID_VERIFIED"]
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 ចាប់ផ្តើម TOP-UP", callback_data=f"start:{order_id}")]])
        
        full_text = base_admin_text + f"📌 *ស្ថានភាព:* {updated_status}\n*(ការបង់ប្រាក់ត្រូវបានផ្ទៀងផ្ទាត់)*"
        await query.edit_message_caption(caption=safe_caption(full_text), reply_markup=keyboard, parse_mode="Markdown")

    elif action == "reject":
        conn.execute("UPDATE orders SET status = 'PAYMENT_REJECTED' WHERE id = ?", (order_id,))
        conn.commit()
        await context.bot.send_message(chat_id=order["telegram_id"], text=f"❌ ការបង់ប្រាក់សម្រាប់ Order #{order_id} មិនអាចផ្ទៀងផ្ទាត់បានទេ ទឺកប្រាក់មិនគ្រប់គ្រាន់ទេ។")
        updated_status = status_text_map["PAYMENT_REJECTED"]
        
        full_text = base_admin_text + f"📌 *ស្ថានភាព:* {updated_status}\n*(ការបង់ប្រាក់ត្រូវបានបដិសេធ)*"
        await query.edit_message_caption(caption=safe_caption(full_text), parse_mode="Markdown")

    elif action == "start":
        conn.execute("UPDATE orders SET status = 'TOPUP_PROCESSING' WHERE id = ?", (order_id,))
        conn.commit()
        updated_status = status_text_map["TOPUP_PROCESSING"]
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ បញ្ចប់ការ TOP-UP", callback_data=f"complete:{order_id}")]])
        
        full_text = base_admin_text + f"📌 *ស្ថានភាព:* {updated_status}\n*(កំពុងដំណើរការ Top-up)*"
        await query.edit_message_caption(caption=safe_caption(full_text), reply_markup=keyboard, parse_mode="Markdown")

    elif action == "complete":
        conn.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))
        conn.commit()
        
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if updated_order:
            receipt_text = generate_order_receipt(updated_order)
            await context.bot.send_message(
                chat_id=updated_order["telegram_id"],
                text=receipt_text,
                parse_mode="Markdown"
            )

        updated_status = status_text_map["COMPLETED"]
        full_text = base_admin_text + f"📌 *ស្ថានភាព:* {updated_status}\n*(ការបញ្ជាទិញបានបញ្ចប់រួចរាល់)*"
        await query.edit_message_caption(caption=safe_caption(full_text), parse_mode="Markdown")

    conn.close()

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = db()
    orders = conn.execute(
        """
        SELECT * FROM orders 
        WHERE telegram_id = ? 
          AND created_at >= date('now', '-1 week')
        ORDER BY id DESC
        """, 
        (user_id,)
    ).fetchall()
    conn.close()

    if not orders:
        msg_text = "🛒 អ្នកមិនទាន់មានប្រវត្តិបញ្ជាទិញក្នុងរយៈពេល ១ សប្តាហ៍ចុងក្រោយនេះទេ។\n(No purchase history in the last week)"
    else:
        status_map = {
            "PAYMENT_REVIEW": "⏳ រង់ចាំការពិនិត្យ",
            "PAID_VERIFIED": "✅ បង់ប្រាក់រួចរាល់", 
            "TOPUP_PROCESSING": "🚀 កំពុងដំណើរការ",
            "COMPLETED": "🎉 រួចរាល់ (Success)",
            "PAYMENT_REJECTED": "❌ មិនបានជោគជ័យ"
        }
        
        msg_text = "🛒 **ប្រវត្តិបញ្ជាទិញ ១ សប្តាហ៍ចុងក្រោយ (Past Week History)៖**\n\n"
        for o in orders:
            status_display = status_map.get(o['status'], o['status'])
            
            try:
                dt = datetime.fromisoformat(o["created_at"])
                formatted_date = dt.strftime("%d-%m-%Y %I:%M %p")
            except Exception:
                formatted_date = o["created_at"]

            msg_text += (
                f"🔹 **Order ID:** `#{o['id']}`\n"
                f"🎮 **ហ្គេម:** {o['game_name']}\n"
                f"📦 **កញ្ចប់:** {o['package_name']}\n"
                f"💵 **តម្លៃ:** `${o['selling_price']:.2f}`\n"
                f"📌 **ស្ថានភាព:** {status_display}\n"
                f"📅 **កាលបរិច្ឆេទ:** `{formatted_date}`\n"
                "-------------------------------------\n"
            )

    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ក្រោយ", callback_data="back")]])
    
    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(msg_text), reply_markup=buttons, parse_mode="Markdown")
    else:
        await query.edit_message_text(text=msg_text, reply_markup=buttons, parse_mode="Markdown")

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    caption_text = (
        "🎮 *ស្វាគមន៍មកកាន់ SAL DIAMOND TOP UP!*\n\n"
        "⚡ រហ័ស • សុវត្ថិភាព • តម្លៃសមរម្យ\n\n"
        "សូមជ្រើសរើសសេវាកម្មខាងក្រោម៖"
    )
    if query.message.photo:
        await query.edit_message_caption(caption=safe_caption(caption_text), reply_markup=main_menu(), parse_mode="Markdown")
    else:
        await query.edit_message_text(text=caption_text, reply_markup=main_menu(), parse_mode="Markdown")

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    conn = db()
    
    # 🧹 លុប Order ណាមួយដែលមានអាយុកាលលើសពី ១ ខែ (៣០ថ្ងៃ) ចោលដោយស្វ័យប្រវត្ត
    conn.execute("DELETE FROM orders WHERE created_at < datetime('now', '-30 days')")
    conn.commit()

    # ទាញយក Order ដែលនៅសល់ក្នុងរយៈពេល ១ ខែចុងក្រោយមកបង្ហាញ
    orders = conn.execute("""
        SELECT * FROM orders
        WHERE created_at >= datetime('now', '-30 days')
        ORDER BY id DESC
        LIMIT 1000
    """).fetchall()
    conn.close()

    if not orders:
        await update.message.reply_text("📋 គ្មាន Order ក្នុងរយៈពេល ១ ខែចុងក្រោយនេះទេ។")
        return

    text = "📋 **ប្រវត្តិ Order (រក្សាទុកត្រឹម ១ ខែចុងក្រោយ):**\n\n"

    status_icons = {
        "COMPLETED": "🎉",
        "PAID_VERIFIED": "✅",
        "TOPUP_PROCESSING": "🚀",
        "PAYMENT_REVIEW": "⏳",
        "PAYMENT_REJECTED": "❌"
    }

    for order in orders:
        username = f"@{order['username']}" if order['username'] else "No username"
        icon = status_icons.get(order['status'], "⌛")
        price = f"${order['selling_price']:.2f}"
        text += f"• `#{order['id']}` | {username} | {price} | {icon} {order['status']}\n"

    await update.message.reply_text(
        text=safe_caption(text, limit=4000), 
        parse_mode="Markdown"
    )

def main():
    if not BOT_TOKEN:
        raise ValueError("Please configure BOT_TOKEN in .env")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(confirm_order, pattern="^confirm_order$")],
        states={WAITING_PAYMENT: [MessageHandler(filters.PHOTO, receive_payment)]},
        fallbacks=[CallbackQueryHandler(cancel_order, pattern="^cancel_order$")],
        per_message=False,
    )

    player_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(choose_package, pattern=r"^pkg:")],
        states={WAITING_PLAYER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_player_id)]},
        fallbacks=[],
        per_message=False,
    )

    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_support_contact, pattern="^support_contact$")],
        states={WAITING_SUPPORT_MSG: [MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO | filters.Document.ALL, receive_support_msg)]},
        fallbacks=[],
        per_message=False,
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("orders", orders_command))
    app.add_handler(player_conv)
    app.add_handler(payment_conv)
    app.add_handler(support_conv)
    app.add_handler(CallbackQueryHandler(choose_game, pattern=r"^game:"))
    app.add_handler(CallbackQueryHandler(my_orders, pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(support_menu, pattern="^support_menu$"))
    app.add_handler(CallbackQueryHandler(support_faq, pattern="^support_faq$"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern=r"^(verify|reject|start|complete):"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    
    # Handler សម្រាប់ឱ្យ Admin Reply សារ Support ទៅអតិថិជន
    app.add_handler(MessageHandler(filters.Chat([GROUP_ID, GROUP_2_ID]) & filters.REPLY & ~filters.COMMAND, reply_to_user))
    
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, direct_support_handler))

    print("Shop Bot is running...")
    app.run_polling()

from keep_alive import keep_alive

if __name__ == "__main__":
    keep_alive()
    main()
