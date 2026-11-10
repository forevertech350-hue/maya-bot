import os
import re
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
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

# 1. /start ትዕዛዝ ሲጻፍ 3ቱ ቁልፎች ብቻ እንዲመጡ ማድረግ
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

# 2. ቁልፎቹ ሲነኩ የሚሰጡት ምላሾች
async def handle_buttons_and_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id

    # A. Your groups: ተጠቃሚው ቦቱን አድሚን ያደረገባቸውን ግሩፖች ማሳየት
    if text == "⚙️ Your groups":
        # እዚህ ጋር ተጠቃሚው ያስተዳደረባቸው ግሩፖች ዝርዝር ይቀርባል
        await message.reply_text(
            "📋 **የእርስዎ ግሩፖች ዝርዝር:**\n\n"
            "• እስካሁን ምንም ግሩፕ አልጨመሩም።\n"
            "ጠቃሚ ምክር: 'Add to group' በመጫን ቦቱን ወደ ግሩፕዎ ይጨምሩ!"
        )
        return

    # B. Add to group: ቦቱን ወደ ግሩፕ ለመጨመር እና አድሚን እንዲሆን የማድረግ ሊንክ
    elif text == "🎈 Add to group":
        bot_username = context.bot.username
        add_link = f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+delete_messages+invite_users+manage_chat"
        
        keyboard = [
            [InlineKeyboardButton("➕ ቦቱን ወደ ግሩፕዎ ይጨምሩ", url=add_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "🤖 **ቦቱን ወደ ግሩፕዎ ለመጨመር:**\n\n"
            "1. ከታች ያለውን ቁልፍ ይጫኑ።\n"
            "2. ቦቱ የሚጨመርበትን ግሩፕ ይምረጡ።\n"
            "3. ግሩፕ ውስጥ **Admin** ማረጋገጫ (Permissions) ሰጥተው ያስገቡት።\n"
            "አንዴ አድሚን ካደረጉት ቦቱ ግሩፑን ሙሉ በሙሉ መቆጣጠር ይጀምራል!",
            reply_markup=reply_markup
        )
        return

    # C. Language: ቋንቋ መቀየሪያ (አማርኛ እና እንግሊዝኛ)
    elif text == "🚩 Language":
        keyboard = [
            [
                InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text("እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Please choose your language:", reply_markup=reply_markup)
        return

    # ግሩፕ ውስጥ የሚደረጉ የሊንክ እና ስድብ ማጣሪያዎች
    if chat_id < 0: # ግሩፕ ከሆነ ብቻ
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            is_admin = member.status in ['creator', 'administrator']
        except Exception:
            is_admin = False

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

# 3. የቋንቋ ምርጫ ማስተካከያ (Inline Button Callback)
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "lang_am":
        user_languages[chat_id] = "am"
        await query.edit_message_text(text="✅ ቋንቋ ወደ **አማርኛ** ተቀይሯል። አሁን ቦቱ ዝግጁ ነው!")
    elif query.data == "lang_en":
        user_languages[chat_id] = "en"
        await query.edit_message_text(text="✅ Language changed to **English**. Bot is ready!")

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons_and_messages))

    print("ቦቱ በሰላም ተጀምሯል...")
    application.run_polling()

if __name__ == "__main__":
    main()
