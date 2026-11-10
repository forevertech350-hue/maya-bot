import os
import re
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")

# Render ፖርት እንዲያገኝ የሚያደርግ ሰርቨር
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Maya Bot is running successfully!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

user_languages = {}
BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "👋 ሰላም! እንኳን ወደ **Maya Bot** በደህና መጡ።\nእባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Please choose your language:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "lang_am":
        user_languages[chat_id] = "am"
        await query.edit_message_text(text="✅ ቋንቋ ወደ **አማርኛ** ተቀይሯል። አሁን ቦቱ ዝግጁ ነው!")
    elif query.data == "lang_en":
        user_languages[chat_id] = "en"
        await query.edit_message_text(text="✅ Language changed to **English**. Bot is ready!")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    chat_id = update.message.chat_id
    lang = user_languages.get(chat_id, "am")

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        name = member.first_name
        if lang == "en":
            await update.message.reply_text(f"Welcome {name} to our group! 🎉")
        else:
            await update.message.reply_text(f"እንኳን ደህና መጣህ/ሽ {name} ወደ ግሩፓችን! 🎉")

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['creator', 'administrator']
    except Exception:
        is_admin = False

    text = message.text

    # ሊንክ ሲላክ ምንም መልእክት ሳይልክ በጸጥታ ማጥፋት
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

def main():
    # ዌብ ሰርቨሩን ማስጀመር
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    # ቦቱን ማዋቀር
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ቦቱ በፖሊንግ ሁነታ እየሰራ ነው...")
    application.run_polling()

if __name__ == "__main__":
    main()
