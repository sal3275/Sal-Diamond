import os
import sqlite3
import html
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()

RECEIPT_BOT_TOKEN = os.getenv("RECEIPT_BOT_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "orders.db")

def db():
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    parts = text.split()
    cmd = parts[0].lower() if parts else ""
    cmd = cmd.split("@")[0]

    # RECEIPT LOOKUP (/pz)
    if cmd == "/pz":
        order_id = None

        if len(parts) >= 2 and parts[1].isdigit():
            order_id = int(parts[1])
        elif msg.reply_to_message:
            reply_text = msg.reply_to_message.caption or msg.reply_to_message.text or ""
            if "#" in reply_text:
                try:
                    raw_id = reply_text.split("#")[1].split()[0].replace("*", "").strip()
                    if raw_id.isdigit():
                        order_id = int(raw_id)
                except Exception:
                    pass

        if not order_id:
            await msg.reply_text(
                "⚠️ <b>របៀបប្រើ <code>/pz</code>:</b>\n\n"
                "• វាយ: <code>/pz &lt;order_id&gt;</code> (ឧទាហរណ៍: <code>/pz 22</code>)\n"
                "• ឬ <b>Reply</b> លើសារ Order រួចវាយ: <code>/pz</code>",
                parse_mode="HTML"
            )
            return

        conn = db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()

        if not order:
            await msg.reply_text(f"❌ រកមិនឃើញ Order #{order_id} នៅក្នុង Database ទេ។")
            return

        status_map = {
            "PAYMENT_REVIEW": "⏳ PENDING REVIEW",
            "PAID_VERIFIED": "✅ PAID & VERIFIED", 
            "TOPUP_PROCESSING": "🚀 PROCESSING",
            "COMPLETED": "🎉 COMPLETED",
            "PAYMENT_REJECTED": "❌ REJECTED"
        }
        status_display = status_map.get(order["status"], f"⏳ {order['status']}")
        username_display = f"@{order['username']}" if order['username'] else "No username"

        receipt_text = (
            "🧾 <b>SAL DIAMOND OFFICIAL RECEIPT</b>\n"
            "=============================\n"
            f"🆔 <b>ORDER ID :</b> #{order['id']}\n"
            f"👤 <b>CUSTOMER :</b> {html.escape(username_display)}\n"
            f"🎮 <b>GAME :</b> {html.escape(order['game_name'] or '')}\n"
            f"📦 <b>PACKAGE :</b> {html.escape(order['package_name'] or '')}\n"
            f"🎯 <b>PLAYER ID:</b> {html.escape(str(order['player_id']))}\n"
            f"💵 <b>TOTAL :</b> ${order['selling_price']:.2f}\n"
            "-----------------------------\n"
            f"📌 <b>STATUS :</b> {html.escape(status_display)}\n"
            f"📅 <b>DATE :</b> {html.escape(str(order['created_at']))}\n"
            "============================-\n"
            "✨ <i>Thank you for choosing our service!</i>"
        )

        await msg.reply_text(receipt_text, parse_mode="HTML")
        return

    # SUPPORT REPLY (/reply)
    target_user_id = None
    reply_text = ""

    if msg.reply_to_message:
        target_text = msg.reply_to_message.caption or msg.reply_to_message.text or ""
        if "User ID:" in target_text:
            try:
                target_user_id = target_text.split("User ID:")[1].split()[0].replace("`", "").strip()
                p = text.split(maxsplit=1)
                reply_text = p[1] if len(p) > 1 else ""
            except Exception as e:
                print(f"Error parsing User ID: {e}")

    if not target_user_id:
        p = text.split(maxsplit=2)
        if len(p) >= 2 and p[1].isdigit():
            target_user_id = p[1]
            reply_text = p[2] if len(p) > 2 else ""

    if not target_user_id:
        await msg.reply_text(
            "⚠️ <b>របៀបឆ្លើយតប:</b>\n\n"
            "1️⃣ ចុច <b>Reply</b> លើសារ Ticket រួចវាយ: <code>/reply &lt;សារ/រូបភាព&gt;</code>\n"
            "2️⃣ ឬ Option B - វាយបញ្ជាក់ ID ផ្ទាល់: <code>/reply &lt;User_ID&gt; &lt;សារ/រូបភាព&gt;</code>\n"
            "3️⃣ មើលវិក្កយបត្រ: <code>/pz &lt;Order_ID&gt;</code>\n"
            "4️⃣ បញ្ជាក់ជោគជ័យ: <code>/success &lt;Order_ID&gt;</code>\n"
            "5️⃣ បដិសេធ Order: <code>/reject &lt;Order_ID&gt; [មូលហេតុ]</code>\n"
            "6️⃣ លុបប្រវត្តិ: <code>/clearhistory id &lt;Order_ID&gt;</code> ឬ <code>/clearhistory user &lt;Username&gt;</code>\n"
            "7️⃣ មើលប្រវត្តិ Order: <code>/orders</code>",
            parse_mode="HTML"
        )
        return

    try:
        target_chat_id = int(target_user_id)

        if msg.photo:
            photo_file_id = msg.photo[-1].file_id
            caption_out = f"💬 <b>សារឆ្លើយតប / Receipt ពី Admin:</b>\n\n{html.escape(reply_text)}" if reply_text else "💬 <b>Receipt ពី Admin</b>"
            await context.bot.send_photo(chat_id=target_chat_id, photo=photo_file_id, caption=caption_out, parse_mode="HTML")
        elif msg.document:
            doc_file_id = msg.document.file_id
            caption_out = f"💬 <b>សារឆ្លើយតបពី Admin:</b>\n\n{html.escape(reply_text)}" if reply_text else "💬 <b>ឯកសារពី Admin</b>"
            await context.bot.send_document(chat_id=target_chat_id, document=doc_file_id, caption=caption_out, parse_mode="HTML")
        else:
            if not reply_text:
                await msg.reply_text("⚠️ សូមបញ្ជាក់សារ ឬផ្ញើរូបភាព receipt!")
                return
            await context.bot.send_message(chat_id=target_chat_id, text=f"💬 <b>សារឆ្លើយតបពី Admin:</b>\n\n{html.escape(reply_text)}", parse_mode="HTML")

        await msg.reply_text(f"✅ បានផ្ញើសារ/Receipt ទៅកាន់ <code>{target_user_id}</code> រួចរាល់!", parse_mode="HTML")

    except Exception as e:
        await msg.reply_text(f"❌ បរាជ័យក្នុងការផ្ញើសារ: {html.escape(str(e))}")

async def success_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to mark an order as COMPLETED by order ID or by replying to an order/receipt message."""
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    parts = text.split()
    
    order_id = None

    if len(parts) >= 2 and parts[1].isdigit():
        order_id = int(parts[1])
    elif msg.reply_to_message:
        reply_text = msg.reply_to_message.caption or msg.reply_to_message.text or ""
        if "#" in reply_text:
            try:
                raw_id = reply_text.split("#")[1].split()[0].replace("*", "").strip()
                if raw_id.isdigit():
                    order_id = int(raw_id)
            except Exception:
                pass

    if not order_id:
        await msg.reply_text(
            "⚠️ <b>របៀបប្រើ <code>/success</code>:</b>\n\n"
            "• វាយ: <code>/success &lt;order_id&gt;</code> (ឧទាហរណ៍: <code>/success 22</code>)\n"
            "• ឬ <b>Reply</b> លើសារ Order រួចវាយ: <code>/success</code>",
            parse_mode="HTML"
        )
        return

    conn = db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    
    if not order:
        conn.close()
        await msg.reply_text(f"❌ រកមិនឃើញ Order #{order_id} នៅក្នុង Database ទេ។")
        return

    conn.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    await msg.reply_text(
        f"✅ Order <b>#{order_id}</b> ត្រូវបានកែប្រែជោគជ័យទៅជា <b>COMPLETED</b> រួចរាល់!",
        parse_mode="HTML"
    )

    try:
        user_chat_id = int(order["telegram_id"])
        notification_text = (
            f"🎉 <b>Your Order #{order_id} has been Completed!</b>\n\n"
            f"🎮 <b>Game:</b> {html.escape(order['game_name'] or '')}\n"
            f"📦 <b>Package:</b> {html.escape(order['package_name'] or '')}\n\n"
            "✨ Thank you for choosing our service!"
        )
        await context.bot.send_message(chat_id=user_chat_id, text=notification_text, parse_mode="HTML")
    except Exception as e:
        print(f"Could not notify user about completion: {e}")

async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to reject an order by order ID or by replying to an order/receipt message."""
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    parts = text.split()
    
    order_id = None
    reason = "No reason provided"

    if len(parts) >= 2 and parts[1].isdigit():
        order_id = int(parts[1])
        if len(parts) > 2:
            reason = " ".join(parts[2:])
    elif msg.reply_to_message:
        reply_text = msg.reply_to_message.caption or msg.reply_to_message.text or ""
        if "#" in reply_text:
            try:
                raw_id = reply_text.split("#")[1].split()[0].replace("*", "").strip()
                if raw_id.isdigit():
                    order_id = int(raw_id)
            except Exception:
                pass
        
        if len(parts) > 1:
            reason = " ".join(parts[1:])

    if not order_id:
        await msg.reply_text(
            "⚠️ <b>របៀបប្រើ <code>/reject</code>:</b>\n\n"
            "• វាយ: <code>/reject &lt;order_id&gt; [មូលហេតុ]</code> (ឧទាហរណ៍: <code>/reject 22 រូបភាពមិនច្បាស់</code>)\n"
            "• ឬ <b>Reply</b> លើសារ Order រួចវាយ: <code>/reject [មូលហេតុ]</code>",
            parse_mode="HTML"
        )
        return

    conn = db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    
    if not order:
        conn.close()
        await msg.reply_text(f"❌ រកមិនឃើញ Order #{order_id} នៅក្នុង Database ទេ។")
        return

    conn.execute("UPDATE orders SET status = 'PAYMENT_REJECTED' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    await msg.reply_text(
        f"❌ Order <b>#{order_id}</b> ត្រូវបានបដិសេធ (REJECTED) រួចរាល់!\n"
        f"📝 មូលហេតុ: {html.escape(reason)}",
        parse_mode="HTML"
    )

    try:
        user_chat_id = int(order["telegram_id"])
        notification_text = (
            f"❌ <b>Your Order #{order_id} has been Rejected</b>\n\n"
            f"🎮 <b>Game:</b> {html.escape(order['game_name'] or '')}\n"
            f"📦 <b>Package:</b> {html.escape(order['package_name'] or '')}\n"
            f"📌 <b>Reason:</b> {html.escape(reason)}\n\n"
            "Please contact support or re-submit with correct payment proof."
        )
        await context.bot.send_message(chat_id=user_chat_id, text=notification_text, parse_mode="HTML")
    except Exception as e:
        print(f"Could not notify user about rejection: {e}")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to clear or delete orders by username or specific order number."""
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    parts = text.split()

    if len(parts) < 2:
        await msg.reply_text(
            "⚠️ <b>របៀបប្រើ <code>/clearhistory</code>:</b>\n\n"
            "• លុបតាម Order ID: <code>/clearhistory id &lt;order_id&gt;</code> (ឧទាហរណ៍: <code>/clearhistory id 22</code>)\n"
            "• លុបតាម Username: <code>/clearhistory user &lt;username&gt;</code> (ឧទាហរណ៍: <code>/clearhistory user johndoe</code>)",
            parse_mode="HTML"
        )
        return

    mode = parts[1].lower()
    conn = db()

    if mode == "id" and len(parts) >= 3:
        target = parts[2].replace("#", "").strip()
        if not target.isdigit():
            conn.close()
            await msg.reply_text("❌ លេខ Order ID មិនត្រឹមត្រូវ។")
            return
        
        order_id = int(target)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()

        if deleted_rows > 0:
            await msg.reply_text(f"🗑️ បានលុបប្រវត្តិ Order <b>#{order_id}</b> ជោគជ័យ!", parse_mode="HTML")
        else:
            await msg.reply_text(f"❌ រកមិនឃើញ Order #{order_id} នៅក្នុង Database ទេ។")

    elif mode == "user" and len(parts) >= 3:
        username = parts[2].replace("@", "").strip()
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE LOWER(username) = LOWER(?)", (username,))
        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()

        if deleted_rows > 0:
            await msg.reply_text(f"🗑️ បានលុបប្រវត្តិ Order សរុបចំនួន <b>{deleted_rows}</b> របស់អតិថិជន <b>@{username}</b> ជោគជ័យ!", parse_mode="HTML")
        else:
            await msg.reply_text(f"❌ រកមិនឃើញប្រវត្តិ Order សម្រាប់ username <b>@{username}</b> ទេ។", parse_mode="HTML")
    else:
        conn.close()
        await msg.reply_text(
            "⚠️ ទម្រង់ពាក្យបញ្ជាមិនត្រឹមត្រូវ។ សូមប្រើ:\n"
            "<code>/clearhistory id &lt;order_id&gt;</code> ឬ <code>/clearhistory user &lt;username&gt;</code>",
            parse_mode="HTML"
        )

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to check recent orders history and show buttons to complete unfinished ones."""
    msg = update.message
    if not msg:
        return

    conn = db()
    # 1. Fetch 1 week history correctly using WHERE
    orders = conn.execute("""
        SELECT * FROM orders 
        WHERE created_at >= date('now', '-7 days') 
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    if not orders:
        await msg.reply_text("📋 គ្មាន Order ក្នុងរយៈពេល ១ សប្ដាហ៍ចុងក្រោយនេះទេ។")
        return

    status_map = {
        "PAYMENT_REVIEW": "⏳ PENDING",
        "PAID_VERIFIED": "✅ VERIFIED",
        "TOPUP_PROCESSING": "🚀 PROCESSING",
        "COMPLETED": "🎉 COMPLETED",
        "PAYMENT_REJECTED": "❌ REJECTED"
    }

    text = "📋 <b>ប្រវត្តិ Order ក្នុងរយៈពេល ១ សប្ដាហ៍ចុងក្រោយ:</b>\n\n"
    keyboard = []

    for order in orders:
        oid = order["id"]
        status = order["status"]
        status_text = status_map.get(status, status)
        username = f"@{order['username']}" if order['username'] else f"ID:{order['player_id']}"

        # Safe line formatting
        safe_username = html.escape(username)
        line = f"• <b>#{oid}</b> | {safe_username} | ${order['selling_price']:.2f} | {status_text}\n"

        # Chunk text if message gets too long (Telegram HTML limit)
        if len(text) + len(line) > 3800:
            await msg.reply_text(text, parse_mode="HTML")
            text = ""

        text += line

        # Add inline action button for pending orders
        if status != "COMPLETED":
            keyboard.append([
                InlineKeyboardButton(f"✅ Make Success #{oid}", callback_data=f"set_success_{oid}"),
                InlineKeyboardButton(f"❌ Make Rejected #{oid}", callback_data=f"set_rejected_{oid}")
            ])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Send final text chunk along with action buttons
    await msg.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks to mark order status as COMPLETED."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("set_success_"):
        try:
            order_id = int(data.split("_")[2])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Invalid Order ID format.")
            return

        conn = db()
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            conn.close()
            await query.edit_message_text(f"❌ រកមិនឃើញ Order #{order_id} ទេ។")
            return

        conn.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()

        await query.edit_message_text(f"✅ Order #{order_id} ត្រូវបានកែប្រែជោគជ័យទៅជា <b>COMPLETED</b> រួចរាល់!", parse_mode="HTML")

def main():
    if not RECEIPT_BOT_TOKEN:
        raise ValueError("Please configure RECEIPT_BOT_TOKEN in .env")

    app = Application.builder().token(RECEIPT_BOT_TOKEN).build()

    app.add_handler(CommandHandler(["reply", "pz"], admin_reply))
    app.add_handler(CommandHandler("success", success_order))
    app.add_handler(CommandHandler("reject", reject_order))
    app.add_handler(CommandHandler("clearhistory", clear_history))
    app.add_handler(CommandHandler("orders", list_orders))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("Receipt & Admin Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()