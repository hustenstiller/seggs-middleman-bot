import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import initialize_db, save_vouch, save_transaction
from transactions import check_transactions
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
import os

# ======================== CONFIG START ========================

TIMEOUT_LIMIT = timedelta(hours=1)
TOKEN = '8430369918:AAHdYDYzrzZYpudD_9-X40KWjTe9wWijNDc'
admin_id = [8236705519, 2146933543]

COINS = {
    "btc": "3ATeuFubPrVzeiYDHdMNcp9S9kRJ3jhGEj",
    "eth": "0x32C096C618301570dD5BEd8bc825440596d6D73B",
    "ltc": "M9DEGnJ9maN62YhPrTSJ2GRzyXLeb7pz5L",
    "sol": "D8J7ZU8n3KB5HM85xfujz3xk9ZiFCi1dTwkFAKV4yut6",
    "ton": "UQAuAC7EWioXH5OIhXPF-3ADRK3A2kXHbVr1tJj6VBxZej8q"
}
print(telegram.__version__)

# ======================== CONFIG END ========================


# start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    if update.message:
        url = "https://t.me/proxy?server=38.60.221.217&port=443&secret=eec29949a4220d69c470d04576eb1784a5617a7572652e6d6963726f736f66742e636f6d"
        keyboard = [
            [InlineKeyboardButton("Connect", url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await message.reply_photo(
            photo=open("assets/welcome.jpeg", "rb"),
            caption="<b>Connect to our MTProxy - fast, private and secure. 🌐</b>",
            reply_markup=reply_markup,
            parse_mode='HTML',
        )
    elif update.business_message:
        url = "https://t.me/proxy?server=38.60.221.217&port=443&secret=eec29949a4220d69c470d04576eb1784a5617a7572652e6d6963726f736f66742e636f6d"
        keyboard = [
            [InlineKeyboardButton("Connect", url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_photo(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            photo=open("assets/welcome.jpeg", "rb"),
            caption="<b>Connect to our MTProxy - fast, private and secure. 🌐</b>",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

# invite message


async def invite_command(update: Update, context: CallbackContext):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    print(message)
    print(f"message: {message}")

    if update.message:
        if message.chat.id not in admin_id:
            return
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
    elif update.business_message:
        if message.from_user.id not in admin_id:
            return
        keyboard = [[InlineKeyboardButton(
            text="Open vouches.my", url="https://vouches.my")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.delete_business_messages(
            business_connection_id=message.business_connection_id,
            message_ids=[message.message_id]
        )

        await context.bot.send_photo(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            photo=open("assets/invite.jpeg", "rb"),
            caption="<b>Your feedback helps build trust and shows others they can count on me. ⚡️</b>",
            reply_markup=reply_markup,
            reply_to_message_id=message.message_id,
            parse_mode="HTML"
        )

# Vouches


async def vouches(update: Update, context: CallbackContext, text: str):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    parts = text.split(" ", 2)
    if len(parts) < 3:
        return

    vouch_for = parts[1]
    comment = parts[2]

    if update.message:
        if message.chat.id in admin_id:
            return
        vouch_by = "@" + update.message.from_user.username if update.message.from_user.username else update.message.from_user.id
    elif update.business_message:
        if message.from_user.id in admin_id:
            return
        vouch_by = "@" + message.chat.username if message.chat.username else message.chat.id

    save_vouch(vouch_by, vouch_for, comment)
    if update.message:
        await update.message.reply_text(text="<b>🤝 Vouch added!</b>", parse_mode="HTML")
    elif update.business_message:
        await context.bot.send_message(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            text="<b>🤝 Vouch added!</b>",
            reply_to_message_id=message.message_id,
            parse_mode="HTML"
        )

# Transactions


async def transactions(update: Update, context: CallbackContext, text: str):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    tx_id, chain = detect_tx_id(text)
    if tx_id:
        chat_id = update.message.chat_id if update.message else message.chat.id
        message_id = update.message.id if update.message else message.message_id

        if chain in ['btc', 'eth', 'sol', 'ton']:
            curr, status = check_transactions(tx_id, chain)
            if curr in ['btc', 'eth', 'sol'] and status == 'confirmed':

                if update.message:
                    save_transaction(tx_id, curr, chat_id, message_id,
                                     business_connection_id, "confirmed")
                    await update.message.reply_text(f"<b>✅ The {curr.upper()} transaction is confirmed!</b>", reply_to_message_id=message_id, parse_mode="HTML")
                elif update.business_message:
                    business_connection_id = message.business_connection_id
                    save_transaction(tx_id, curr, chat_id,
                                     message_id, business_connection_id,  "confirmed")
                    await context.bot.send_message(
                        business_connection_id=business_connection_id,
                        chat_id=message.chat.id,
                        text=f"<b>✅ The {curr.upper()} transaction is confirmed!</b>",
                        reply_to_message_id=message.message_id,
                        parse_mode="HTML"
                    )
                return

        if update.message:
            save_transaction(tx_id, curr, chat_id, message_id)
            await update.message.reply_text("<b>⏳ I will let you know when your transaction has hit 1 confirmation!</b>", parse_mode="HTML")
        elif update.business_message:
            business_connection_id = message.business_connection_id
            save_transaction(tx_id, curr, chat_id, message_id,
                             business_connection_id)
            await context.bot.send_message(
                business_connection_id=business_connection_id,
                chat_id=message.chat.id,
                text="<b>⏳ I will let you know when your transaction has hit 1 confirmation!</b>",
                reply_to_message_id=message.message_id,
                parse_mode="HTML"
            )


# Detect transactions


def detect_tx_id(text: str):
    text = text.strip()
    
    if re.search(r'https?://|www\.', text, re.IGNORECASE):
        return None, None

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


# show wallets

async def wallet(update: Update, context: CallbackContext, coin: str, amount):
    message = update.message or update.business_message
    if not message or not message.text:
        return

    address = COINS.get(coin)
    if not address:
        return

    chat_id = update.message.chat_id if update.message else message.chat.id
    message_id = update.message.id if update.message else message.message_id

    if update.message:
        if message.chat.id not in admin_id:
            return
        await update.message.reply_text(
            text=f"<b>Send {coin} to: <code>{address}</code> amount: <code>${amount}</code> </b>",
            parse_mode="HTML"
        )
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
    elif update.business_message:
        if message.from_user.id not in admin_id:
            return

        await context.bot.delete_business_messages(
            business_connection_id=message.business_connection_id,
            message_ids=[message_id]
        )
        await context.bot.send_message(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            text=f"<b>Send {coin} to: <code>{address}</code> amount: <code>${amount}</code> </b>",
            parse_mode="HTML"
        )


#  Handle commands


async def command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message or not message.text:
        return
    text = message.text.strip().lower()

    if text == "/start" or text == '/proxy':
        await start_command(update, context)
    elif text == "/invite":
        await invite_command(update, context)

    # Vouch message
    elif text.lower().startswith("vouch"):
        await vouches(update, context, text)

    else:
        await transactions(update, context, text)

    for coin in COINS.keys():
        chain = text.split()[0][1:]
        if (coin == chain):
            parts = text.split(" ", 2)
            amount = parts[1]
            await wallet(update, context, chain, amount)
        else:
            continue



# Checking pending transactions


async def check_pending_transactions(context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect("vouches.db") as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, tx_id, chain, message_id, chat_id, business_connection_id, date FROM transactions WHERE status = 'pending'")
        rows = cur.fetchall()

        current_time = datetime.now(timezone.utc)

        for id, tx_id, chain, message_id, chat_id, business_connection_id, date in rows:
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

                    if business_connection_id != '':
                        await context.bot.send_message(business_connection_id=business_connection_id,
                                                       chat_id=chat_id, text=f"<b>✅ The {curr.upper()} transaction is confirmed!</b>",
                                                       reply_to_message_id=message_id,
                                                       parse_mode="HTML"
                                                       )
                    else:
                        await context.bot.send_message(chat_id=chat_id, text=f"<b>✅ The {curr.upper()} transaction is confirmed!</b>", reply_to_message_id=message_id, parse_mode="HTML")
                time.sleep(5)


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, command_handler))

    job_queue = application.job_queue
    job_queue.run_repeating(check_pending_transactions, interval=60)

    print("Bot is starting...")
    
    if os.getenv("HEROKU") == "1":
        port = int(os.getenv("PORT", "8443"))
        webhook_url = f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/{TOKEN}"
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=webhook_url
        )
    else:
        print("Running locally with polling...")
        application.run_polling()
    print("Bot stopped.")


if __name__ == '__main__':
    initialize_db()
    main()
