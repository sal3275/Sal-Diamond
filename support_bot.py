import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()

# Token សម្រាប់ Support Bot (សូមដាក់ Bot Token ថ្មីដែលបានពី @BotFather ក្នុង .env)
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")

def parse_env_int(var_name, default_val):
    val = os.getenv(var_name, str(default_val))
    if "=" in val:
        val = val.split("=")[-1]
    try:
        return int(val.strip())
    except ValueError:
        return default_val

# Group សម្រាប់ទទួល Support Tickets
GROUP_ID = parse_env_int("GROUP_ID", -1003957662857)
GROUP_2_ID = parse_env_int("GROUP_2_ID", 0)

async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 *ស្វាគមន៍មកកាន់មជ្ឈមណ្ឌលជំនួយ SAL DIAMOND SUPPORT!*\n\n"
        "📝 សូមសរសេរសារ បញ្ហា ឬសំណួររបស់អ្នកមកទីនេះ ក្រុមការងារ Admin នឹងឆ្លើយតបជូនលោកអ្នកឆាប់ៗនេះ។",
        parse_mode="Markdown"
    )

async def receive_user_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"👇 *របៀបឆ្លើយតប:* Reply សារនេះក្នុង Group ដើម្បីឆ្លើយតបទៅកាន់អតិថិជន។"
    )

    target_chat = GROUP_2_ID if GROUP_2_ID != 0 else GROUP_ID

    try:
        if msg.photo:
            await context.bot.send_photo(chat_id=target_chat, photo=msg.photo[-1].file_id, caption=ticket_info, parse_mode="Markdown")
        elif msg.document:
            await context.bot.send_document(chat_id=target_chat, document=msg.document.file_id, caption=ticket_info, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=target_chat, text=ticket_info, parse_mode="Markdown")

        await msg.reply_text("✅ សាររបស់អ្នកត្រូវបានផ្ញើទៅកាន់ក្រុមការងារ Admin រួចរាល់ហើយ! សូមរង់ចាំការឆ្លើយតប។")
    except Exception as e:
        print(f"Error sending support message: {e}")
        await msg.reply_text("❌ មានបញ្ហាក្នុងการផ្ញើសារ សូមព្យាយាមម្តងទៀត។")

async def admin_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        return

    replied_text = message.reply_to_message.caption or message.reply_to_message.text or ""
    if "User ID:" not in replied_text:
        return

    try:
        for line in replied_text.split("\n"):
            if "User ID:" in line:
                user_id_str = line.split("`")[1] if "`" in line else line.split(":")[-1].strip()
                target_user_id = int(user_id_str)
                
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
                break
    except Exception as e:
        print(f"❌ Error replying to user: {e}")
        await message.reply_text(f"❌ មិនអាចផ្ញើសារទៅកាន់អតិថិជនបានទេ: {e}")

def main():
    if not SUPPORT_BOT_TOKEN:
        raise ValueError("Please configure SUPPORT_BOT_TOKEN in .env")

    app = Application.builder().token(SUPPORT_BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start_support))
    app.add_handler(MessageHandler(filters.Chat([GROUP_ID, GROUP_2_ID]) & filters.REPLY & ~filters.COMMAND, admin_reply_to_user))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, receive_user_msg))

    print("Support Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
