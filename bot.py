import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database import initialize_db, save_vouch, save_transaction, delete_vouch_from_local_db
from transactions import check_transactions
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
import os
import mysql_handler


TIMEOUT_LIMIT = timedelta(hours=1)
TOKEN = '8430369918:AAHdYDYzrzZYpudD_9-X40KWjTe9wWijNDc'
admin_id = [8236705519]

COINS = {
    "btc": "3ATeuFubPrVzeiYDHdMNcp9S9kRJ3jhGEj",
    "eth": "0x32C096C618301570dD5BEd8bc825440596d6D73B",
    "ltc": "M9DEGnJ9maN62YhPrTSJ2GRzyXLeb7pz5L",
    "sol": "D8J7ZU8n3KB5HM85xfujz3xk9ZiFCi1dTwkFAKV4yut6",
    "ton": "UQAuAC7EWioXH5OIhXPF-3ADRK3A2kXHbVr1tJj6VBxZej8q"
}
print(f"python-telegram-bot version: {telegram.__version__}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.business_message
        url = "https://t.me/proxy?server=38.60.221.217&port=443&secret=eec29949a4220d69c470d04576eb1784a5617a7572652e6d6963726f736f66742e636f6d"
        keyboard = [[InlineKeyboardButton("Connect", url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        caption = "<b>Connect to our MTProxy - fast, private and secure. 🌐</b>"
        photo_path = "assets/welcome.jpeg"

        if update.message:
            await message.reply_photo(photo=photo_path, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        elif update.business_message:
            await context.bot.send_photo(business_connection_id=message.business_connection_id, chat_id=message.chat.id, photo=photo_path, caption=caption, reply_markup=reply_markup, parse_mode="HTML")
        
        try:
            if update.message:
                await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            elif update.business_message:
                await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
        except telegram.error.BadRequest as e:
            print(f"Info: Could not delete /start command: {e}. (Normal for old messages)")

    except FileNotFoundError:
        print("ERROR: Asset file 'assets/welcome.jpeg' not found.")
    except Exception as e:
        print(f"Error in start_command: {e}")

async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.business_message
        
        response_text = (
            "<b>💬 How to vouch me:</b>\n\n"
            "Simply send a message starting with the word — vouch —\n"
            "followed by your text.\n\n"
            "<b>Example:</b>\n"
            "<code>vouch great and smooth deal, fast and trusted 🤝</code>\n\n"
            "Your vouch will be automatically posted on my site — vouches.my ✅"
        )

        web_app_info = WebAppInfo(url="https://vouches.my")
        keyboard = [[InlineKeyboardButton(text="vouches.my", web_app=web_app_info)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await message.reply_text(text=response_text, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
        elif update.business_message:
            url_keyboard = [[InlineKeyboardButton(text="vouches.my", url="https://vouches.my")]]
            url_reply_markup = InlineKeyboardMarkup(url_keyboard)
            await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=response_text, reply_markup=url_reply_markup, parse_mode="HTML", disable_web_page_preview=True)

        try:
            if update.message:
                await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            elif update.business_message:
                await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
        except telegram.error.BadRequest as e:
            print(f"Info: Could not delete /invite command: {e}. (Normal for old messages)")

    except Exception as e:
        print(f"Error in invite_command: {e}")
        print(f"Error in invite_command: {e}")

async def vouches(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        message = update.message or update.business_message
        parts = text.split()
        if len(parts) < 2: return

        vouch_for, comment = (parts[1], " ".join(parts[2:])) if len(parts) > 2 and parts[1].startswith('@') else ("@general", " ".join(parts[1:]))
        vouch_by = f"@{message.from_user.username}" if message.from_user.username else f"User:{message.from_user.id}"
        
        save_vouch(vouch_by, vouch_for, comment)
        mysql_handler.add_vouch_to_mysql(vouch_by=str(vouch_by), vouch_text=comment)
        
        confirmation_text = "<b>🤝 Vouch added!</b>"
        if update.message:
            await message.reply_text(text=confirmation_text, parse_mode="HTML")
        elif update.business_message:
            await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=confirmation_text, reply_to_message_id=message.message_id, parse_mode="HTML")
    except Exception as e:
        print(f"Error in vouches function: {e}")

async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        message = update.message or update.business_message
        tx_id, chain = detect_tx_id(text)
        if not tx_id: return

        business_connection_id = message.business_connection_id if update.business_message else None
        
        curr, status = check_transactions(tx_id, chain)
        if status == 'confirmed':
            reply_text = f"<b>✅ The {curr.upper()} transaction is already confirmed!</b>"
            save_transaction(tx_id, curr, message.chat.id, message.message_id, business_connection_id, "confirmed")
        else:
            reply_text = "<b>⏳ I will let you know when your transaction has hit 1 confirmation!</b>"
            save_transaction(tx_id, chain, message.chat.id, message.message_id, business_connection_id)

        if update.message:
            await message.reply_text(reply_text, parse_mode="HTML")
        elif update.business_message:
            await context.bot.send_message(business_connection_id=business_connection_id, chat_id=message.chat.id, text=reply_text, reply_to_message_id=message.message_id, parse_mode="HTML")
    except Exception as e:
        print(f"Error in transactions function: {e}")

def detect_tx_id(text: str):
    text = text.strip()
    if re.search(r'https?://|www\.', text, re.IGNORECASE): return None, None
    patterns = { "btc": re.compile(r"\b[a-fA-F0-9]{64}\b"), "eth": re.compile(r"0x[a-fA-F0-9]{64}"), "sol": re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{43,88}\b"), "ton": re.compile(r"\b[A-Za-z0-9+/_-]{42,100}={0,2}") }
    for chain, pattern in patterns.items():
        if match := pattern.search(text): return match.group(), chain
    return None, None

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, coin: str, amount: str):
    try:
        message = update.message or update.business_message
        address = COINS.get(coin)
        if not address: return

        text_to_send = f"<b>Send {coin.upper()} to:</b>\n<code>{address}</code>\n<b>Amount:</b> <code>{amount}</code>"
        
        if update.message:
            await message.reply_text(text=text_to_send, parse_mode="HTML")
        elif update.business_message:
            await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=text_to_send, parse_mode="HTML")

        try:
            if update.message:
                await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            elif update.business_message:
                await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
        except telegram.error.BadRequest as e:
            print(f"Info: Could not delete admin's wallet command: {e}. (Normal for old messages)")
    except Exception as e:
        print(f"Error in wallet function: {e}")

async def delete_vouch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.business_message
        if not message.reply_to_message or not message.reply_to_message.text:
            await message.reply_text("<b>Usage:</b> Reply to the vouch message you want to delete with <code>/del_vouch</code>.", parse_mode="HTML")
            return

        vouch_text_to_delete = mysql_handler.get_vouch_text_from_message(message.reply_to_message.text)
        if not vouch_text_to_delete:
            await message.reply_text("⚠️ Could not parse the vouch text to be deleted.")
            return

        mysql_success = mysql_handler.delete_vouch_from_mysql(vouch_text_to_delete)
        local_db_success = delete_vouch_from_local_db(vouch_text_to_delete)

        if mysql_success or local_db_success:
            await message.reply_text("✅ Vouch has been deleted from the database(s).")
        else:
            await message.reply_text("⚠️ Vouch could not be found in the databases.")

        try:
            if update.message:
                await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            elif update.business_message:
                await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
        except telegram.error.BadRequest as e:
            print(f"Info: Could not delete admin's /del_vouch command: {e}. (This is normal for old messages).")
    except Exception as e:
        print(f"A critical error occurred in delete_vouch_command: {e}")


async def master_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles ALL incoming messages and routes them based on the new permission rules."""
    try:
        message = update.message or update.business_message
        if not message or not message.text or not message.from_user:
            return
            
        text = message.text.strip()
        user_id = message.from_user.id
        command_parts = text.split()
        command = command_parts[0].lower()

        if user_id in admin_id:
            if command.startswith("vouch"):
                print(f"Info: Admin {user_id} tried to use 'vouch'. Action ignored.")
                return

            if command in ["/start", "/proxy"]:
                await start_command(update, context)
                return
            if command == "/invite":
                await invite_command(update, context)
                return
            if command == "/del_vouch":
                await delete_vouch_command(update, context)
                return
            
            coin = command[1:] if command.startswith('/') else None
            if coin in COINS.keys():
                if len(command_parts) > 1:
                    await wallet(update, context, coin, command_parts[1])
                else:
                    await message.reply_text(f"<b>Usage:</b> <code>/{coin} [amount]</code>", parse_mode="HTML")
                return
            
            await transactions(update, context, text)
            return
        else:
            if command.startswith("vouch"):
                await vouches(update, context, text)
                return

    except Exception as e:
        print(f"FATAL ERROR in master_handler, update was not processed: {e}")


async def check_pending_transactions(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect("vouches.db") as conn:
        cur = conn.cursor()
        rows = cur.execute("SELECT id, tx_id, chain, message_id, chat_id, business_connection_id, date FROM transactions WHERE status = 'pending'").fetchall()
        current_time = datetime.now(timezone.utc)
        for id, tx_id, chain, message_id, chat_id, business_connection_id, date in rows:
            created_at = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            if current_time - created_at > TIMEOUT_LIMIT:
                cur.execute("UPDATE transactions SET status = 'failed' WHERE id = ?", (id,))
                continue
            curr, status = check_transactions(tx_id, chain)
            if status == 'confirmed':
                cur.execute("UPDATE transactions SET chain = ?, status = 'confirmed' WHERE id = ?", (curr, id))
                reply_text = f"<b>✅ The {curr.upper()} transaction is confirmed!</b>"
                try:
                    if business_connection_id:
                        await context.bot.send_message(business_connection_id=business_connection_id, chat_id=chat_id, text=reply_text, reply_to_message_id=message_id, parse_mode="HTML")
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=reply_text, reply_to_message_id=message_id, parse_mode="HTML")
                except Exception as e:
                    print(f"Failed to send confirmation for tx {tx_id}: {e}")
            time.sleep(5)
        conn.commit()


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT, master_handler))
    job_queue = application.job_queue
    job_queue.run_repeating(check_pending_transactions, interval=60, name="pending_tx_checker")
    print("Business Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Bot has stopped.")


if __name__ == '__main__':
    initialize_db()
    main()