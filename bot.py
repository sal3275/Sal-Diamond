import re

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.reply_to_message:
        return

    # អនុញ្ញាតឱ្យដំណើរការតែក្នុង Group Admin ទាំងពីរប៉ុណ្ណោះ
    valid_groups = [g for g in [GROUP_ID, GROUP_2_ID] if g != 0]
    if valid_groups and message.chat.id not in valid_groups:
        return

    replied_text = message.reply_to_message.caption or message.reply_to_message.text or ""
    if "User ID:" not in replied_text:
        return

    try:
        # ប្រើ Regular Expression ដើម្បីទាញយក User ID យ៉ាងត្រឹមត្រូវដោយស្វ័យប្រវត្ត (មិនខ្វល់រឿង HTML tags ឬ Backticks)
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
