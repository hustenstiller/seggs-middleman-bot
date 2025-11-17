# admin_commands.py
from telegram import Update
from telegram.ext import ContextTypes
import mysql_handler  # optional, if you store chat history in DB

async def delete_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Deletes all messages in a business chat for both participants.
    Only usable by admins.
    """
    message = update.message or update.business_message
    if not message:
        return

    chat_id = message.chat.id
    business_connection_id = getattr(message, 'business_connection_id', None)
    user_id = message.from_user.id

    # Admin check
    admin_id = [8236705519]  # Replace or import from your main bot
    if user_id not in admin_id:
        await message.reply_text("⚠️ You are not authorized to use this command.")
        return

    # Optional: Delete chat messages from DB
    try:
        mysql_handler.delete_chat_from_mysql(chat_id)
    except Exception as e:
        print(f"Warning: Could not delete chat from DB: {e}")

    # Fetch last N messages from DB or track manually
    # Here, we assume you track last 100 messages for safety
    message_ids_to_delete = list(range(message.message_id, max(message.message_id - 100, 0), -1))

    # Delete messages
    try:
        if business_connection_id:
            await context.bot.delete_business_messages(
                business_connection_id=business_connection_id,
                message_ids=message_ids_to_delete
            )
        else:
            for msg_id in message_ids_to_delete:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except:
                    pass  # ignore errors for messages already deleted

        await message.reply_text("✅ Chat cleared successfully.")
    except Exception as e:
        await message.reply_text(f"⚠️ Failed to delete chat: {e}")
