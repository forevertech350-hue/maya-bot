import os
import re
import asyncio
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Maya Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

user_languages = {}
custom_welcomes = {}
BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]

# የተሻሻለው ፖተርን፡ ሊንኮችን እና በ @ የሚጀምሩ ዩዘርናሞችን ሙሉ በሙሉ ይይዛል
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+|@[a-zA-Z0-9_]{5,})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("⚙️ Your groups")],
        [KeyboardButton("🎈 Add to group")],
        [KeyboardButton("🚩 Language")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if update.message:
        await update.message.reply_text(
            "👋 ሰላም! እንኳን ወደ **Maya Bot** በደህና መጡ።\nእባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ:",
            reply_markup=reply_markup
        )

async def delete_after_delay(message, delay=60):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.message.chat_id
    custom_text = custom_welcomes.get(chat_id)

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        name = member.first_name
        if custom_text:
            welcome_msg = custom_text.replace("{name}", name)
        else:
            welcome_msg = f"እንኳን ወደ ግሩፓችን በደህና መጣችሁ {name}! 🎉"
        
        sent_msg = await update.message.reply_text(welcome_msg)
        asyncio.create_task(delete_after_delay(sent_msg, 60))

async def handle_buttons_and_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id

    if text == "⚙️ Your groups":
        await message.reply_text("📋 **የእርስዎ ግሩፖች ዝርዝር:**\n\nእስካሁን ምንም ግሩፕ አልጨመሩም።")
        return
    elif text == "🎈 Add to group":
        bot_username = context.bot.username
        add_link = f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+delete_messages+invite_users+manage_chat"
        keyboard = [[InlineKeyboardButton("➕ ቦቱን ወደ ግሩፕዎ ይጨምሩ", url=add_link)]]
        await message.reply_text("🤖 **ቦቱን ወደ ግሩፕዎ ለማስገባት ከታች ያለውን ቁልፍ ይጫኑ:**", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif text == "🚩 Language":
        keyboard = [
            [
                InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ]
        await message.reply_text("እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Choose your language:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ግሩፕ ውስጥ የሚደረግ ጥብቅ የሊንክ እና የዩዘርናም ቁጥጥር (Owner እና Admin ብቻ)
    if chat_id < 0:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['creator', 'administrator']
        except Exception:
            is_admin = False

        # አድሚን ወይም ኦነር ካልሆነ እና ሊንክ ወይም @ ዩዘርናም ከላከ ወዲያውኑ ማጥፋት
        if not is_admin and re.search(URL_PATTERN, text, re.IGNORECASE):
            try:
                await message.delete()
            except Exception:
                pass
            return

        if not is_admin:
            for word in BAD_WORDS:
                if word.lower() in text.lower():
                    try:
                        await message.delete()
                        await context.bot.restrict_chat_member(
                            chat_id=chat_id,
                            user_id=user_id,
                            permissions={"can_send_messages": False}
                        )
                    except Exception:
                        pass
                    break

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "lang_am":
        user_languages[chat_id] = "am"
        await query.edit_message_text(text="✅ ቋንቋ ወደ **አማርኛ** ተቀይሯል።")
    elif query.data == "lang_en":
        user_languages[chat_id] = "en"
        await query.edit_message_text(text="✅ Language changed to **English**.")

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons_and_messages))

    print("ቦቱ በሰላም ተጀምሯል...")
    application.run_polling()

if __name__ == "__main__":
    main()
