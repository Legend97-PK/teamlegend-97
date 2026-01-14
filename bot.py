import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import Database
from flask import Flask, request  # Added for webhook support

# Configuration
BOT_TOKEN = os.getenv('8292521025:AAFKKkYr4Gy_OZD5Blge441e-J2MjRTCubQ')  # Ensure this is set in your environment
ADMIN_IDS = [int(id.strip()) for id in os.getenv('8122951733', '7384592378').split(',') if id.strip()]  # Comma-separated admin IDs from env
db = Database()

# Logging setup
logging.basicConfig(level=logging.INFO)

# AI Support function (simple rule-based; extend with API for advanced responses)
def ai_response(query):
    responses = {
        'how to get numbers': 'Click GET NUMBER ☎️ and select a country.',
        'balance': 'Check your balance with 💰 My Balance.',
        'default': 'I\'m here to help! Ask about numbers, referrals, or support.'
    }
    return responses.get(query.lower(), responses['default'])

# User Panel Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.add_user(user_id)
    keyboard = [
        [InlineKeyboardButton("GET NUMBER ☎️", callback_data='get_number')],
        [InlineKeyboardButton("📦 Stock ↗️", callback_data='stock')],
        [InlineKeyboardButton("💰 My Balance", callback_data='balance')],
        [InlineKeyboardButton("📊 Status", callback_data='status')],
        [InlineKeyboardButton("🌍 Available Traffic", callback_data='traffic')],
        [InlineKeyboardButton("👤 Friend Invite", callback_data='invite')],
        [InlineKeyboardButton("💰 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("☎️ Support", callback_data='support')]
    ]
    await update.message.reply_text('Welcome! Choose an option:', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'get_number':
        countries = db.get_countries()
        if not countries:
            await query.edit_message_text('No countries available.')
            return
        keyboard = [[InlineKeyboardButton(c, callback_data=f'country_{c}')] for c in countries]
        keyboard.append([InlineKeyboardButton('Back', callback_data='back')])
        await query.edit_message_text('Select a country:', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('country_'):
        country = data.split('_', 1)[1]
        numbers = db.get_numbers(country)
        if not numbers:
            await query.edit_message_text('No numbers available for this country.')
            return
        text = f"Numbers for {country}:\n" + '\n'.join([f"`{n['number']}`" for n in numbers])
        otp_link = db.get_setting('otp_group') or 'https://t.me/example'
        keyboard = [
            [InlineKeyboardButton('Join OTP Group', url=otp_link)],
            [InlineKeyboardButton('Refresh', callback_data=f'refresh_{country}')],
            [InlineKeyboardButton('Back', callback_data='get_number')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith('refresh_'):
        country = data.split('_', 1)[1]
        # Simulate refresh by fetching new numbers (in real DB, mark old as used)
        numbers = db.get_numbers(country)
        text = f"Refreshed numbers for {country}:\n" + '\n'.join([f"`{n['number']}`" for n in numbers])
        otp_link = db.get_setting('otp_group') or 'https://t.me/example'
        keyboard = [
            [InlineKeyboardButton('Join OTP Group', url=otp_link)],
            [InlineKeyboardButton('Refresh', callback_data=f'refresh_{country}')],
            [InlineKeyboardButton('Back', callback_data='get_number')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'stock':
        countries = db.get_countries()
        await query.edit_message_text(f'Available Stock:\n' + '\n'.join(countries) if countries else 'No stock.')

    elif data == 'balance':
        user = db.get_user(user_id)
        await query.edit_message_text(f'Your Balance: {user[1]} invites.')

    elif data == 'status':
        total_users = db.get_total_users()
        await query.edit_message_text(f'Bot Status: Online\nTotal Users: {total_users}')

    elif data == 'traffic':
        alert = db.get_setting('traffic_alert') or 'No alerts.'
        await query.edit_message_text(f'Available Traffic: {alert}')

    elif data == 'invite':
        user = db.get_user(user_id)
        await query.edit_message_text(f'Your Referral Link: {user[2]}\nShare it to earn invites!')

    elif data == 'withdraw':
        user = db.get_user(user_id)
        if user[1] >= 50:
            admin_id = ADMIN_IDS[0] if ADMIN_IDS else 'admin_username'  # Link to first admin
            await query.edit_message_text(f'Contact Admin for reward: https://t.me/{admin_id}')
        else:
            await query.edit_message_text('You need 50 invites to withdraw.')

    elif data == 'support':
        await query.edit_message_text('Contact support: @admin_username')

    elif data == 'back':
        await start(update, context)  # Reuse start for back

# Admin Panel Handlers
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text('Access denied.')
        return
    keyboard = [
        [InlineKeyboardButton('Upload Numbers', callback_data='admin_upload')],
        [InlineKeyboardButton('Broadcast', callback_data='admin_broadcast')],
        [InlineKeyboardButton('Manage Countries', callback_data='admin_manage')],
        [InlineKeyboardButton('Analytics', callback_data='admin_analytics')],
        [InlineKeyboardButton('Settings', callback_data='admin_settings')]
    ]
    await update.message.reply_text('Admin Panel:', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer('Access denied.')
        return
    await query.answer()
    data = query.data

    if data == 'admin_upload':
        await query.edit_message_text('Send a .txt file with numbers, and reply with country name.')

    elif data == 'admin_broadcast':
        await query.edit_message_text('Send the message to broadcast (supports media).')

    elif data == 'admin_manage':
        countries = db.get_countries()
        keyboard = [[InlineKeyboardButton(f'Delete {c}', callback_data=f'delete_{c}')] for c in countries]
        keyboard.append([InlineKeyboardButton('Wipe All', callback_data='wipe_all')])
        await query.edit_message_text('Manage Countries:', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('delete_'):
        country = data.split('_', 1)[1]
        db.delete_country(country)
        await query.edit_message_text(f'Deleted {country}.')

    elif data == 'wipe_all':
        db.wipe_all()
        await query.edit_message_text('All countries wiped.')

    elif data == 'admin_analytics':
        total_users = db.get_total_users()
        await query.edit_message_text(f'Total Users: {total_users}')

    elif data == 'admin_settings':
        await query.edit_message_text('Send key-value pairs to update settings (e.g., otp_group=https://t.me/group).')

# Message Handlers
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    file = await update.message.document.get_file()
    content = (await file.download_as_bytearray()).decode('utf-8')
    numbers = [line.strip() for line in content.split('\n') if line.strip()]
    context.user_data['pending_numbers'] = numbers
    await update.message.reply_text('Numbers uploaded. Now send the country name.')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in ADMIN_IDS and 'pending_numbers' in context.user_data:
        country = text
        db.add_numbers(country, context.user_data['pending_numbers'], user_id)
        del context.user_data['pending_numbers']
        await update.message.reply_text(f'Numbers added for {country}.')
    elif text.startswith('/ai '):  # AI support
        query = text[4:]
        response = ai_response(query)
        await update.message.reply_text(response)
    else:
        # Handle broadcasts or other text (extend for full broadcast logic if needed)
        pass

# Referral Handling (via deep link in /start)
async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if args and args[0].isdigit():
        invited_by = int(args[0])
        db.add_user(user_id, invited_by)
        db.update_balance(invited_by, 1)
        await update.message.reply_text('Welcome! You were invited.')

# Background Scheduler for Auto-Cleanup
scheduler = AsyncIOScheduler()
scheduler.add_job(db.cleanup_expired, 'interval', hours=1)
scheduler.start()

# Application Setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler('start', handle_referral))  # For referrals
app.add_handler(CommandHandler('admin', admin_panel))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern='admin_.*'))
app.add_handler(MessageHandler(filters.Document.FileExtension('txt'), handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# Webhook setup for Vercel
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), app.bot)
    app.bot.process_update(update)
    return 'OK'

if __name__ == '__main__':
    # For local testing, use polling
    if os.getenv('LOCAL'):
        app.run_polling()
    else:
        # For Vercel, set webhook
        webhook_url = f"https://{os.getenv('VERCEL_URL')}/webhook"
        app.bot.set_webhook(url=webhook_url)
        flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))