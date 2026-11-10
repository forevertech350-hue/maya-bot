import os
import re
import asyncio
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")

# Render ፖርት እንዲያገኝ የሚያደርግ ዌብ ሰርቨር
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Maya Advanced Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# የቋንቋ ምርጫዎች መዝገብ (ማከማቻ)
user_languages = {} # chat_id -> 'am' ወይም 'en'

BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

# 1. /start ትዕዛዝ ሲጻፍ ቋንቋ የሚያስመርጥ አማራጭ (Inline Keyboard)
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
            "👋 ሰላም! እንኳን ወደ **Maya Bot** በደህና መጡ።\nእütfen የሚፈልጉትን ቋንቋ ይምረጡ / Please choose your language:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# የቋንቋ ምርጫ መልስ ሰጪ (Callback Query)
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

# 2. አዲስ ሰው ሲገባ (በተመረጠው ቋንቋ መሰረት ሰላምታ)
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.message.chat_id
    lang = user_languages.get(chat_id, "am") # ነባሪው አማርኛ ነው

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        name = member.first_name
        
        if lang == "en":
            welcome_text = f"Welcome {name} to our group! 🎉 Please read the rules and enjoy your stay."
        else:
            welcome_text = f"እንኳን ደህና መጣህ/ሽ {name} ወደ ግሩፓችን! 🎉 እባክዎ ደንቦቹን ያክብሩ።"
            
        await update.message.reply_text(welcome_text)

# 3. መልዕክቶችን መቆጣጠር (ሊንክ ያለ ማሳሰቢያ ማጥፋት እና ስድብ መቆጣጠር)
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

    # ከኦነር/አድሚን ውጪ ሊንክ ሲላክ ምንም መልእክት ሳይልክ ወዲያውኑ ማጥፋት (Silent Delete)
    if not is_admin and re.search(URL_PATTERN, text, re.IGNORECASE):
        try:
            await message.delete()
        except Exception:
            pass
        return

    # የተከለከሉ ቃላትን መቆጣጠር
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

# 4. በተወሰነ ሰዓት (Schedule/Background Loop) ሙዚቃ ወይም ማስታወቂያ የሚለቀቅበት ሲስተም
async def scheduled_music_sender(application):
    await asyncio.sleep(10) # ቦቱ ሲጀመር ትንሽ ይጠብቃል
    while True:
        # እዚህ ጋር ሙዚቃ የሚለቀቅበትን ሰዓት ወይም ክፍተት ማስተካከል ይቻላል (ለምሳሌ በየ 2 ሰዓቱ)
        # ለምሳሌ ያህል ሙዚቃ ሊንክ ወይም ጽሁፍ መላክ ይቻላል
        # await application.bot.send_message(chat_id="የግሩፕ_아이디_ወይም_ዩዘር", text="🎵 የሰዓቱ ምርጥ ሙዚቃ/ዜና እነሆ!")
        await asyncio.sleep(7200) # በየ 2 ሰዓቱ (በሰከንድ)

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    
    # ሀንድለሮች (Handlers)
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_handler))
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ዘመናዊው Maya Bot በሰላም ተጀምሯል...")
    
    # ራስ-ሰር ስራዎችን ከፖሊንግ ጋር ማስኬድ
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_music_sender(bot_app))
    
    bot_app.run_polling()

if __name__ == "__main__":
    main()
