import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from transactions import check_transactions
import mysql_handler
from email_handler import send_vouch_notification
import re
import time
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import asyncio
import secrets
import string
from currency_converter import get_live_rates, get_price
from pytz import timezone as pytz_timezone
from pytz import UnknownTimeZoneError
from fastapi import FastAPI, Request, Response
import uvicorn

load_dotenv()

TIMEOUT_LIMIT = timedelta(hours=1)
TOKEN = os.getenv("TOKEN")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

# Webhook Configuration Logic
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Fallback: Construct URL if not explicitly provided in config
if not WEBHOOK_URL and HEROKU_APP_NAME:
    WEBHOOK_URL = f"https://{HEROKU_APP_NAME}.herokuapp.com"
    
admin_id = [8236705519]

PLACEHOLDER_EMAIL = "user@vouches.my"
PLACEHOLDER_IP = "1.1.1.1" 

FK_API_URL = os.getenv("FK_API_URL")
FK_SHOP_ID = os.getenv("FK_SHOP_ID")
FK_API_KEY = os.getenv("FK_API_KEY")

PAYMENT_SYSTEMS = {
    "btc": 24,
    "ltc": 25,
    "eth": 26,
    "usdttrc": 15,
    "usdterc": 14,
    "ton": 45,
    "bnb": 17,
    "tron": 39,
    "fkusd": 2,       
    "fkrub": 1,   
    "yoomoney": 6,
    "cardrub": 36,  
    "visarub": 4,
    "mastercardrub": 8,
    "mir": 12,
    "cc": 13,
    "sbp": 42, 
}

PAYMENT_LIMITS = {
    'fkrub':         {'min': 1001, 'max': 300000, 'currency': 'RUB'},
    'fkusd':         {'min': 1, 'max': 5000, 'currency': 'USD'},
    'cardrub':       {'min': 5001, 'max': 100000, 'currency': 'RUB'},
    'yoomoney':      {'min': 1001, 'max': 100000, 'currency': 'RUB'},
    'visarub':       {'min': 1001, 'max': 150000, 'currency': 'RUB'},
    'mastercardrub': {'min': 1001, 'max': 150000, 'currency': 'RUB'},
    'mir':           {'min': 1000, 'max': 100000, 'currency': 'RUB'},
    'cc':            {'min': 1001, 'max': 100000, 'currency': 'RUB'},
    'sbp':           {'min': 1001, 'max': 100000, 'currency': 'RUB'},
    'btc':           {'min': 0.0001, 'max': 20, 'currency': 'BTC'},
    'ltc':           {'min': 0.01, 'max': 1000, 'currency': 'LTC'},
    'eth':           {'min': 0.0001, 'max': 1000, 'currency': 'ETH'},
    'usdterc':       {'min': 10, 'max': 100000, 'currency': 'USDT'},
    'usdttrc':       {'min': 2.5, 'max': 100000, 'currency': 'USDT'},
    'ton':           {'min': 0.1, 'max': 100000, 'currency': 'TON'},
    'bnb':           {'min': 0.01, 'max': 10000, 'currency': 'BNB'},
    'tron':          {'min': 10, 'max': 100000, 'currency': 'TRX'},
}

COINS = {
    "btc": "3ATeuFubPrVzeiYDHdMNcp9S9kRJ3jhGEj",
    "eth": "0x32C096C618301570dD5BEd8bc825440596d6D73B",
    "ltc": "M9DEGnJ9maN62YhPrTSJ2GRzyXLeb7pz5L",
    "sol": "D8J7ZU8n3KB5HM85xfujz3xk9ZiFCi1dTwkFAKV4yut6",
    "ton": "UQAuAC7EWioXH5OIhXPF-3ADRK3A2kXHbVr1tJj6VBxZej8q"
}

SUPPORTED_CRYPTO = ['btc', 'eth', 'sol', 'ltc', 'xmr', 'ton', 'bnb', 'trx', 'xrp']
CONVERT_SUPPORTED = SUPPORTED_CRYPTO + ['rub']

CONVERT_USAGE_TEXT = (
    "<b>Usage:</b> <code>.convert_{currency} [amount]</code>\n\n"
    "<b>Examples:</b>\n"
    "• <u>Crypto/RUB to USD:</u>\n"
    "  <code>.convert_btc 0.5</code>\n\n"
    "• <u>USD to Crypto/RUB:</u>\n"
    "  <code>.convert_ton 100$</code>\n\n"
    f"<b>Supported Currencies:</b> {', '.join(CONVERT_SUPPORTED)}"
)

app = FastAPI(docs_url=None, redoc_url=None)
application = Application.builder().token(TOKEN).build()

print(f"python-telegram-bot version: {telegram.__version__}")

async def cleanup_deleted_vouches(context: ContextTypes.DEFAULT_TYPE):
    print("Running scheduled job: Cleaning up deleted vouches...")
    try:
        await asyncio.to_thread(mysql_handler.permanently_delete_vouches)
    except Exception as e:
        print(f"An unexpected error occurred during the vouch cleanup job: {e}")


@app.on_event("startup")
async def startup_event():
    print("Initializing Telegram Bot Application...")
    application.add_handler(MessageHandler(filters.ALL, master_handler))
    job_queue = application.job_queue
    job_queue.run_repeating(check_pending_transactions, interval=180)
    job_queue.run_repeating(check_paid_invoices, interval=90)
    job_queue.run_repeating(check_due_reminders, interval=60)
    job_queue.run_repeating(cleanup_deleted_vouches, interval=300)
    
    await application.initialize()
    
    # Set the webhook using the configured URL and Secret Token
    if WEBHOOK_URL:
        webhook_endpoint = f"{WEBHOOK_URL}/{SECRET_TOKEN}"
        print(f"Setting webhook to: {webhook_endpoint}")
        await application.bot.set_webhook(url=webhook_endpoint, allowed_updates=Update.ALL_TYPES)
    else:
        print("ERROR: WEBHOOK_URL is not set and HEROKU_APP_NAME is missing. Webhook not set.")
        
    await job_queue.start()
    print("Startup complete. Bot is running.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down...")
    application.job_queue.stop()
    await application.shutdown()
    print("Shutdown complete.")

@app.get("/")
async def health_check():
    """Health check endpoint for the pinger. Returns 200 OK."""
    return Response(status_code=200)

@app.post(f"/{SECRET_TOKEN}")
async def telegram_webhook(request: Request):
    """Handles incoming updates from Telegram."""
    try:
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=application.bot)
        await application.process_update(update)
        return Response(status_code=200)
    except Exception:
        return Response(status_code=500)

async def process_vouch_in_background(context: ContextTypes.DEFAULT_TYPE):
    try:
        job_data = context.job.data
        vouch_by = job_data['vouch_by']
        comment = job_data['comment']
        user_id = job_data['user_id']

        print(f"Background job started for vouch by {vouch_by} (User ID: {user_id})")
        success = await asyncio.to_thread(
            mysql_handler.add_vouch_to_mysql, vouch_by=vouch_by, vouch_text=comment, user_id=user_id
        )
        if success:
            await asyncio.to_thread(send_vouch_notification, vouch_by, comment)
            await asyncio.to_thread(mysql_handler.revoke_vouch_permission, user_id)
            print(f"Vouch added and permission revoked for user {user_id}.")
        
        print(f"Background job finished for vouch by {vouch_by}")

    except Exception as e:
        print(f"Error in background vouch processing: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    welcome_caption = (
        "<b>Welcome to my Thread</b>\n\n"
        "Read this <b>carefully</b> before contacting me.\n\n"
        " • No “hi,” “hello,” or small talk — get <b>straight</b> to the point about what you want.\n\n"
        "• Always have your <b>crypto ready</b> before messaging me about any deal. No time-wasting or “I’ll buy later.”\n\n"
        " • Make sure you <b>read my TOS</b> in full before we proceed. By messaging me, you automatically agree to them.\n\n"
        "• After a smooth transaction, <b>leave a vouch</b> — it helps build trust in the community."
    )
    photo_path = "assets/welocome_thread.jpg"
    keyboard = [[InlineKeyboardButton("ToS", url="https://tos.vouches.my")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.message:
            await message.reply_photo(photo=photo_path, caption=welcome_caption, reply_markup=reply_markup, parse_mode='HTML')
        elif update.business_message:
            await context.bot.send_photo(business_connection_id=message.business_connection_id, chat_id=message.chat.id, photo=photo_path, caption=welcome_caption, reply_markup=reply_markup, parse_mode="HTML")
    except FileNotFoundError:
        print(f"ERROR: Welcome image not found at '{photo_path}'. Sending text-only fallback.")
        if update.message:
            await message.reply_text(text=welcome_caption, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)
        elif update.business_message:
            await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=welcome_caption, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
    
    # Second message for .start command
    second_message = "Hi! 👋 If you want to message me anonymously, please start a chat with my bot @seggsbot — it's available anytime!"
    if update.message:
        await message.reply_text(text=second_message, parse_mode='HTML')
    elif update.business_message:
        await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=second_message, parse_mode="HTML")

    try:
        if update.message:
            await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        elif update.business_message:
            await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
    except telegram.error.BadRequest as e:
        print(f"Info: Could not delete .start command: {e}. (Normal for old messages)")


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    
    response_text = (
        "<b>💬 How to vouch me:</b>\n\n"
        "<b>Simply send a message starting with the word — vouch —</b>\n"
        "<b>followed by your text.</b>\n\n"
        "<b>Example:</b>\n"
        "<code>vouch great and smooth deal, fast and trusted 🤝</code>\n\n"
        "<b>Your vouch will be automatically posted on my site — vouches.my ✅</b>"
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
        print(f"Info: Could not delete .invite command: {e}. (Normal for old messages)")


async def vouches(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    message = update.message or update.business_message
    user_id = message.from_user.id

    if not mysql_handler.has_permission_to_vouch(user_id):
        await message.reply_text("⚠️ You do not have permission to submit a vouch currently.", parse_mode="HTML")
        return

    parts = text.split()
    if len(parts) < 2: return
    
    vouch_for, comment = (parts[1], " ".join(parts[2:])) if len(parts) > 2 and parts[1].startswith('@') else ("@general", " ".join(parts[1:]))
    vouch_by = f"@{message.from_user.username}" if message.from_user.username else f"User:{message.from_user.id}"
    
    confirmation_text = "<b>🤝 Vouch added!</b>"
    if update.message:
        await message.reply_text(text=confirmation_text, parse_mode="HTML")
    elif update.business_message:
        await context.bot.send_message(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            text=confirmation_text,
            reply_to_message_id=message.message_id,
            parse_mode="HTML"
        )
    
    context.job_queue.run_once(
        process_vouch_in_background,
        when=1,
        data={'vouch_by': vouch_by, 'comment': comment, 'user_id': user_id},
        name=f"vouch-{message.from_user.id}-{int(time.time())}"
    )


async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    message = update.message or update.business_message
    tx_id, chain = detect_tx_id(text)
    if not tx_id: return

    business_connection_id = message.business_connection_id if update.business_message else None
    
    curr, status = check_transactions(tx_id, chain)
    if status == 'confirmed':
        reply_text = f"<b>✅ The {curr.upper()} transaction is already confirmed!</b>"
        mysql_handler.save_transaction_to_mysql(tx_id, curr, message.chat.id, message.message_id, business_connection_id, "confirmed")
    else:
        reply_text = "<b>⏳ I will let you know when your transaction has hit 1 confirmation!</b>"
        mysql_handler.save_transaction_to_mysql(tx_id, chain, message.chat.id, message.message_id, business_connection_id)

    if update.message:
        await message.reply_text(reply_text, parse_mode="HTML")
    elif update.business_message:
        await context.bot.send_message(business_connection_id=business_connection_id, chat_id=message.chat.id, text=reply_text, reply_to_message_id=message.message_id, parse_mode="HTML")


def detect_tx_id(text: str):
    text = text.strip()
    if re.search(r'https?://|www\.', text, re.IGNORECASE): return None, None
    patterns = { "btc": re.compile(r"\b[a-fA-F0-9]{64}\b"), "eth": re.compile(r"0x[a-fA-F0-9]{64}"), "sol": re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{43,88}\b"), "ton": re.compile(r"\b[A-Za-z0-9+/_-]{42,100}={0,2}") }
    for chain, pattern in patterns.items():
        if match := pattern.search(text): return match.group(), chain
    return None, None


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, coin: str, amount: str):
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


async def delete_vouch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.reply_text("<b>Usage:</b> Reply to the vouch message you want to delete with <code>.del_vouch</code>.", parse_mode="HTML")
        return

    vouch_text_to_delete = mysql_handler.get_vouch_text_from_message(message.reply_to_message.text)
    if not vouch_text_to_delete:
        await message.reply_text("⚠️ Could not parse the vouch text to be deleted.")
        return
    mysql_success = mysql_handler.delete_vouch_from_mysql(vouch_text_to_delete)

    if mysql_success:
        await message.reply_text("✅ Vouch has been deleted from the database.")
    else:
        await message.reply_text("⚠️ Vouch could not be found in the database.")

    try:
        if update.message:
            await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        elif update.business_message:
            await context.bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
    except telegram.error.BadRequest as e:
        print(f"Info: Could not delete admin's .del_vouch command: {e}. (This is normal for old messages).")

    
async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the .remind command for all users."""
    message = update.message or update.business_message
    command_parts = message.text.split()

    if len(command_parts) != 3:
        await message.reply_text(
            "<b>Usage:</b> <code>.remind DD/MM/YYYY HH:MM</code>\n"
            "<b>Example:</b> <code>.remind 01/01/2026 00:00</code>",
            parse_mode="HTML"
        )
        await delete_command_message(update, context)
        return

    date_str, time_str = command_parts[1], command_parts[2]
    datetime_str = f"{date_str} {time_str}"
    
    try:
        ist_tz = pytz_timezone("Europe/Berlin")
        naive_dt = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
        ist_dt = ist_tz.localize(naive_dt)
        utc_dt = ist_dt.astimezone(timezone.utc)
        
        if utc_dt < datetime.now(timezone.utc):
            await message.reply_text("⚠️ The reminder time cannot be in the past.", parse_mode="HTML")
            await delete_command_message(update, context)
            return

    except (ValueError, UnknownTimeZoneError) as e:
        print(f"Error parsing date/time for reminder: {e}")
        await message.reply_text(
            "⚠️ Invalid date/time format. Please use <code>DD/MM/YYYY HH:MM</code>.",
            parse_mode="HTML"
        )
        await delete_command_message(update, context)
        return

    context.user_data['reminder_datetime_utc'] = utc_dt
    
    await message.reply_text(
        "<b>Reminder time set.</b>\n\n"
        "Please send the text for the reminder now.",
        parse_mode="HTML"
    )
    await delete_command_message(update, context)


async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles cryptocurrency and RUB conversion commands."""
    message = update.message or update.business_message
    command_parts = message.text.split()
    command = command_parts[0].lower()

    if command == ".convert" or len(command_parts) != 2:
        await message.reply_text(CONVERT_USAGE_TEXT, parse_mode="HTML")
        await delete_command_message(update, context)
        return

    currency_symbol = command.split('_')[1]
    if currency_symbol not in CONVERT_SUPPORTED:
        await message.reply_text(f"⚠️ <b>Unsupported Currency:</b> {currency_symbol.upper()}", parse_mode="HTML")
        await delete_command_message(update, context)
        return
        
    price_in_usd = await get_price(currency_symbol)
    if price_in_usd is None:
        await message.reply_text(f"⚠️ Could not fetch the price for {currency_symbol.upper()}. Please try again later.", parse_mode="HTML")
        await delete_command_message(update, context)
        return
    amount_str = command_parts[1]
    reply_text = ""

    try:
        if amount_str.endswith('$'):
            usd_amount = float(amount_str.strip('$'))
            currency_amount = usd_amount / price_in_usd
            
            if currency_symbol == 'rub':
                reply_text = f"<code>${usd_amount:,.2f}</code> is equal to <code>{currency_amount:,.2f} RUB</code>"
            else:
                reply_text = f"<code>${usd_amount:,.2f}</code> is equal to <code>{currency_amount:,.8f} {currency_symbol.upper()}</code>"
        else:
            currency_amount = float(amount_str)
            usd_amount = currency_amount * price_in_usd
            
            if currency_symbol == 'rub':
                 reply_text = f"<code>{currency_amount:,.2f} RUB</code> is equal to <code>${usd_amount:,.2f}</code>"
            else:
                reply_text = f"<code>{currency_amount:,.8f} {currency_symbol.upper()}</code> is equal to <code>${usd_amount:,.2f}</code>"

    except ValueError:
        await message.reply_text("⚠️ Invalid amount specified. Please use a valid number.", parse_mode="HTML")
        await delete_command_message(update, context)
        return
        
    await message.reply_text(reply_text, parse_mode="HTML")
    await delete_command_message(update, context)


async def delete_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A helper function to safely delete the user's original command message."""
    try:
        message = update.message or update.business_message
        if not message:
            return

        if update.message:
            await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        elif update.business_message:
            await context.bot.delete_business_messages(
                business_connection_id=message.business_connection_id,
                message_ids=[message.message_id]
            )
    except telegram.error.BadRequest as e:
        print(f"Info: Could not delete user's command: {e}. (Normal for old messages).")

async def master_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles ALL incoming messages and routes them."""
    try:
        message = update.message or update.business_message
        if not message or not message.from_user:
            return
        
        user_id = message.from_user.id
        if mysql_handler.is_new_user(user_id):
            mysql_handler.add_user(user_id)
            
            welcome_caption = (
                "<b>Welcome to my Thread</b>\n\n"
                "Read this <b>carefully</b> before contacting me.\n\n"
                " • No “hi,” “hello,” or small talk — get <b>straight</b> to the point about what you want.\n\n"
                "• Always have your <b>crypto ready</b> before messaging me about any deal. No time-wasting or “I’ll buy later.”\n\n"
                " • Make sure you <b>read my TOS</b> in full before we proceed. By messaging me, you automatically agree to them.\n\n"
                "• After a smooth transaction, <b>leave a vouch</b> — it helps build trust in the community."
            )
            photo_path = "assets/welocome_thread.jpg"
            keyboard = [[InlineKeyboardButton("ToS", url="https://tos.vouches.my")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                if update.message:
                    await message.reply_photo(photo=photo_path, caption=welcome_caption, reply_markup=reply_markup, parse_mode='HTML')
                elif update.business_message:
                    await context.bot.send_photo(business_connection_id=message.business_connection_id, chat_id=message.chat.id, photo=photo_path, caption=welcome_caption, reply_markup=reply_markup, parse_mode="HTML")
            except FileNotFoundError:
                print(f"ERROR: Welcome image not found at '{photo_path}'. Sending text-only fallback.")
                if update.message:
                    await message.reply_text(text=welcome_caption, reply_markup=reply_markup, parse_mode='HTML', disable_web_page_preview=True)
                elif update.business_message:
                    await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=welcome_caption, reply_markup=reply_markup, parse_mode="HTML", disable_web_page_preview=True)
            
            # Second message for new users
            second_message_text = "Hi! 👋 If you want to message me anonymously, please start a chat with my bot @seggsbot — it's available anytime!"
            if update.message:
                await message.reply_text(text=second_message_text, parse_mode='HTML')
            elif update.business_message:
                await context.bot.send_message(business_connection_id=message.business_connection_id, chat_id=message.chat.id, text=second_message_text, parse_mode="HTML")

        if 'reminder_datetime_utc' in context.user_data:
            reminder_text = message.text
            remind_at_utc = context.user_data.pop('reminder_datetime_utc')
            business_connection_id = message.business_connection_id if update.business_message else None
            success = mysql_handler.save_reminder_to_mysql(remind_at=remind_at_utc, reminder_text=reminder_text, chat_id=message.chat.id, business_connection_id=business_connection_id)
            if success:
                ist_tz = pytz_timezone("Europe/Berlin")
                remind_at_ist = remind_at_utc.astimezone(ist_tz)
                confirmation_text = (f"<b>✅ Reminder set!</b>\n\n" f"I will remind you on:\n" f"<code>{remind_at_ist.strftime('%d/%m/%Y at %H:%M')} (German Time)</code>")
                await message.reply_text(confirmation_text, parse_mode="HTML")
            else:
                await message.reply_text("⚠️ There was an error saving your reminder. Please try again.", parse_mode="HTML")
            return

        if not message.text:
            return

        text = message.text.strip()
        command_parts = text.split()
        command = command_parts[0].lower()

        if user_id in admin_id:
            if command == ".start": await start_command(update, context); return
            if command == ".invite": await invite_command(update, context); return
            if command == ".del_vouch": await delete_vouch_command(update, context); return
            if command == ".reset":
                user_to_reset_id = message.chat.id
                if await asyncio.to_thread(mysql_handler.grant_vouch_permission, user_to_reset_id):
                    await message.reply_text("✅ This user's vouching permission has been reset. They can now vouch again.", parse_mode="HTML")
                else:
                    await message.reply_text("⚠️ Could not find this user to reset their permission.", parse_mode="HTML")
                await delete_command_message(update, context)
                return
            if command.startswith(".invoice"):
                if len(command_parts) < 2 or not command_parts[1].replace('.', '', 1).isdigit():
                    await message.reply_text("<b>Usage:</b> <code>.invoice[_{method}] [amount]</code>\n\n<b>Example:</b> <code>.invoice_btc 10.50</code>", parse_mode="HTML")
                    await delete_command_message(update, context)
                    return
                amount = float(command_parts[1])
                method_key = command.split('_')[1].lower() if '_' in command else None
                if method_key and method_key in PAYMENT_LIMITS:
                    limit_info = PAYMENT_LIMITS[method_key]
                    limit_currency = limit_info['currency']
                    min_limit_native = limit_info['min']
                    max_limit_native = limit_info['max']
                    symbols_to_fetch = ['USD']
                    if limit_currency not in ['USD', 'RUB']:
                        symbols_to_fetch.append(limit_currency)
                    rates = await get_live_rates(symbols_to_fetch, ['USD', 'RUB'])
                    if not rates:
                        print("WARNING: Could not fetch live rates. Bypassing limit check.")
                    else:
                        min_limit_usd, max_limit_usd = 0, 0
                        if limit_currency == 'USD':
                            min_limit_usd, max_limit_usd = min_limit_native, max_limit_native
                        elif limit_currency == 'RUB':
                            usd_to_rub = rates.get('USD', {}).get('RUB')
                            if usd_to_rub:
                                min_limit_usd, max_limit_usd = min_limit_native / usd_to_rub, max_limit_native / usd_to_rub
                        else:
                            crypto_price_usd = rates.get(limit_currency, {}).get('USD')
                            if crypto_price_usd:
                                min_limit_usd, max_limit_usd = min_limit_native * crypto_price_usd, max_limit_native * crypto_price_usd

                        if max_limit_usd > 0 and not (min_limit_usd <= amount <= max_limit_usd):
                            warning_text = (f"⚠️ <b>Limit Exceeded for {method_key.upper()}</b>\n\n" f"Amount <code>${amount:.2f}</code> is outside the allowed range.\n\n" f"<b>Min:</b> <code>${min_limit_usd:.2f}</code> | <b>Max:</b> <code>${max_limit_usd:.2f}</code>")
                            await message.reply_text(warning_text, parse_mode="HTML")
                            await delete_command_message(update, context)
                            return
                order_id = str(int(time.time())) + str(secrets.randbelow(1000)).zfill(3)
                alphabet = string.ascii_letters + string.digits
                url_key = ''.join(secrets.choice(alphabet) for i in range(12))
                invoice_url = f"https://vouches.my/payment/{url_key}"
                invoice_text = (f"✅ <b>Invoice Successfully Created</b>\n\n" f"Your invoice for <b>${amount:.2f}</b> has been generated.\n\n" f"Please <b>review the details</b> and ensure all information is accurate.\n\n" f"<b>Status:</b> Pending Payment\n\n" f"Click the button below to\n<b>proceed with the payment</b>.")
                keyboard = [[InlineKeyboardButton("💳 Pay Securely", url=invoice_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                sent_message = await message.reply_text(text=invoice_text, reply_markup=reply_markup, parse_mode="HTML")
                payment_system_id = PAYMENT_SYSTEMS.get(method_key)
                mysql_handler.save_invoice_to_mysql(order_id, amount, url_key, payment_system_id, chat_id=sent_message.chat.id, message_id=sent_message.message_id)
                await delete_command_message(update, context)
                return
            coin = command[1:] if command.startswith('.') else None
            if coin in COINS.keys():
                if len(command_parts) > 1:
                    await wallet(update, context, coin, command_parts[1])
                else:
                    await message.reply_text(f"<b>Usage:</b> <code>.{coin} [amount]</code>", parse_mode="HTML")
                    await delete_command_message(update, context)
                return

        if command == ".convert" or command.startswith(".convert_"):
            await convert_command(update, context)
            return
            
        if command == ".remind": await remind_command(update, context); return

        if text.lower().startswith("vouch"):
            if user_id not in admin_id:
                await vouches(update, context, text)
            return
            
        await transactions(update, context, text); return

    except telegram.error.BadRequest as e:
        if "Business_connection_invalid" in str(e):
            user_info = update.effective_user.id if update.effective_user else "Unknown User"
            print(f"Info: Ignored a command from User ID {user_info} due to an invalid business connection. The user must reconnect their business account.")
        else:
            print(f"FATAL ERROR in master_handler (BadRequest): {e}")
    except Exception as e:
        print(f"FATAL ERROR in master_handler (General): {e}")
