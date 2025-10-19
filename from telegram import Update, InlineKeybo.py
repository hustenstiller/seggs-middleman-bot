from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import initialize_db, save_vouch, save_transaction
from transactions import check_transactions
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone

TOKEN = '8430369918:AAHdYDYzrzZYpudD_9-X40KWjTe9wWijNDc'

# start command


async def start_command(update: Update, context: CallbackContext):
    url = "https://t.me/proxy?server=38.60.221.217&port=443&secret=eec29949a4220d69c470d04576eb1784a5617a7572652e6d6963726f736f66742e636f6d"
    keyboard = [
        [InlineKeyboardButton("Connect", url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = update.message or update.business_message
    await message.reply_photo(
        photo=open("assets/welcome.jpeg", "rb"),
        caption="<b>Connect to our MTProxy - fast, private and secure. 🌐</b>",
        reply_markup=reply_markup,
        parse_mode='HTML',
    )

# invite message


async def invite_command(update: Update, context: CallbackContext):
    web_app_info = WebAppInfo(url="https://vouches.my")
    keyboard = [
        [InlineKeyboardButton(text="vouches.my", web_app=web_app_info)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=open("assets/invite.jpeg", "rb"),
        caption="<b>Your feedback helps build trust and shows others they can count on me. ⚡️</b>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# handle other messages


async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text

    # Vouch message
    if text.lower().startswith("vouch"):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            await update.message.reply_text("<b>Usage: vouch @username your message</b>", parse_mode="HTML")
            return

        vouch_for = parts[1]
        message = parts[2]
        vouch_by = "@" + update.message.from_user.username if update.message.from_user.username else update.message.from_user.id

        save_vouch(vouch_by, vouch_for, message)
        await update.message.reply_text("<b>🤝 Vouch added!</b>", parse_mode="HTML")

    # hash detection
    tx_id, chain = detect_tx_id(text)
    if tx_id:
        chat_id = update.message.chat_id
        message_id = update.message.id

        if chain in ['btc', 'eth', 'sol', 'ton']:
            curr, status = check_transactions(tx_id, chain)
            if curr in ['btc', 'eth', 'sol'] and status == 'confirmed':
                save_transaction(tx_id, curr, chat_id,
                                 message_id, "confirmed")
                await update.message.reply_text(f"<b>✅ The {curr.upper()} transaction is confirmed!</b>", reply_to_message_id=message_id, parse_mode="HTML")
                return

        save_transaction(tx_id, curr, chat_id, message_id)
        await update.message.reply_text("<b>⏳ I will let you know when your transaction has hit 1 confirmation!</b>", parse_mode="HTML")

# detect tx


def detect_tx_id(text: str):
    text = text.strip()

    btc_pattern = re.compile(r"\b[a-fA-F0-9]{64}\b")
    eth_pattern = re.compile(r"0x[a-fA-F0-9]{64}")
    sol_pattern = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{43,88}\b")
    ton_pattern = re.compile(r"\b[A-Za-z0-9+/_-]{42,100}={0,2}")

    if btc_pattern.search(text):
        return btc_pattern.search(text).group(), "btc"
    elif eth_pattern.search(text):
        return eth_pattern.search(text).group(), "eth"
    elif sol_pattern.search(text):
        return sol_pattern.search(text).group(), "sol"
    elif ton_pattern.search(text):
        return ton_pattern.search(text).group(), "ton"
    else:
        return None, None


# Checking pending transactions
TIMEOUT_LIMIT = timedelta(hours=1)


async def check_pending_transactions(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect("vouches.db") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tx_id, chain, message_id, chat_id, date FROM transactions WHERE status = 'pending'")
        rows = cur.fetchall()

        current_time = datetime.now(timezone.utc)

        for id, tx_id, chain, message_id, chat_id, date in rows:
            created_at = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            created_utc = created_at.replace(tzinfo=timezone.utc)
            if current_time - created_utc > TIMEOUT_LIMIT:
                print(
                    f"😢 sorry {tx_id} is expired current_time: {current_time}, created_at: {created_utc}")
                cur.execute(
                    "UPDATE transactions SET status = 'failed' WHERE id = ?", (id, ))
                continue

            if chain in ['btc', 'eth', 'sol', 'ton', 'usdt', 'ltc']:
                curr, status = check_transactions(tx_id, chain)
                print(f"📨 status: {status}")
                if status == 'confirmed':
                    cur.execute(
                        "UPDATE transactions SET chain = ?, status = 'confirmed' WHERE id = ?", (curr, id, ))
                    await context.bot.send_message(chat_id=chat_id, text=f"<b>✅ The {curr.upper()} transaction is confirmed!</b>", reply_to_message_id=message_id, parse_mode="HTML")
                time.sleep(5)

# show wallets

COINS = {
    "btc": "aab4b78ba0a3e0a2c2687a8558a5d2280dbb5a03c9a691fb9a0038db9f7b6785",
    "eth": "0x1234567890abcdef1234567890abcdef12345678",
    "ltc": "Lc123abc456def789ghi012jkl345mno678",
    "sol": "So1Nabc1234567890soladdress",
    "usdt": "TR5nPApi9sY4CjDcjrbAhcKf2LrUH6c9ko",
    "ton": "UQABjCHLXLNK6Hh5-K-nGIuZVA3IoqudGXiSEg2fkcazbKXK"
}


async def wallet(update: Update, context: CallbackContext):
    command = update.message.text.split()[0][1:]
    coin = command.lower()

    address = COINS.get(coin)
    if not address:
        await update.message.reply_text("❌ Unknown coin.")
        return

    await update.message.reply_text(
        text=f"<b>{coin} address: </b> <code>{address}</code>",
        parse_mode="HTML"
    )

    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    await context.bot.delete_message(
        chat_id=chat_id,
        message_id=message_id
    )


async def handle_business_message(update: Update, context):
    # Check if the message is from a business connection
    if update.message.business_connection_id:
        business_connection_id = update.message.business_connection_id
        user_message = update.message.text

        # Log or process the message from the business account
        print(
            f"Received message from business connection {business_connection_id}: {user_message}")

        # Send a reply back to the business account
        await update.message.reply_text(f"Thank you for your message, business account! You said: {user_message}")
    else:
        # Handle regular messages not from a business connection
        await update.message.reply_text("I received a regular message.")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("invite", invite_command))
    # application.add_handler(MessageHandler(
    #     filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_business_message))

    # wallets
    for coin in COINS.keys():
        application.add_handler(CommandHandler(coin, wallet))

    job_queue = application.job_queue
    job_queue.run_repeating(check_pending_transactions, interval=60)

    print("Bot is starting...")
    application.run_polling()
    print("Bot stopped.")


if __name__ == '__main__':
    initialize_db()
    main()
