import os
import re
import asyncio
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")

# Render ፖርት እንዲያገኝ የሚያደርግ ሰርቨር
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Maya Ultimate Bot is running successfully!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

# ማከማቻዎች (Databases / Dictionaries)
user_languages = {} # ቋንቋ ማከማቻ
custom_welcomes = {} # የግሩፕ የእንኳን ደህና መጣችሁ መልእክት ማከማቻ
target_group_id = None # ሙዚቃ እና ፖስት የሚለቀቅበት ዋና ግሩፕ ਆይዲ

BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

# 1. /start ትዕዛዝ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ],
        [
            InlineKeyboardButton("🎵 የሙዚቃ ሰዓት ማስተካከያ", callback_data="menu_music"),
            InlineKeyboardButton("ℹ️ የቦቱ ደንቦች", callback_data="menu_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "👋 ሰላም! እንኳን ወደ **Maya Ultimate Bot** በደህና መጡ።\nእባክዎ የሚፈልጉትን አማራጭ ይምረጡ:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# 2. የቁልፍ መጫጫ (Buttons Handler)
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
    elif query.data == "menu_music":
        await query.message.reply_text("🎵 ሙዚቃ በራስ-ሰር በሰዓቱ እንዲለቀቅ ግሩፕዎ ውስጥ አድሚን መሆን አለብኝ እና `/setchannel` መጠቀም ይቻላል።")
    elif query.data == "menu_help":
        await query.message.reply_text("ℹ️ ይህ ቦት ግሩፕን ከስድብ እና ከሊንክ ይጠብቃል፣ አዲስ ሰዎችን ይቀበላል፣ እንዲሁም በሰዓቱ ሙዚቃ ይለቃል።")

# 3. የእንኳን ደህና መጣችሁ መልእክት ማስተካከያ ትዕዛዝ (/setwelcome)
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    
    # አድሚን መሆኑን ማረጋገጥ
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ['creator', 'administrator']:
            await message.reply_text("⚠️ ይህንን ትዕዛዝ መጠቀም የሚችሉት አድሚኖች ብቻ ናቸው!")
            return
    except Exception:
        return

    text_args = " ".join(context.args)
    if not text_args:
        await message.reply_text("⚠️ እባክዎ የሚፈልጉትን መልእክት አብረው ይጻፉ።\nምሳሌ: `/setwelcome እንኳን ደህና መጡ! {name}`", parse_mode="Markdown")
        return

    custom_welcomes[chat_id] = text_args
    await message.reply_text("✅ የእንኳን ደህና መጣችሁ መልእክት በተሳካ ሁኔታ ተስተካክሏል!")

# 4. አዲስ ሰው ሲገባ
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global target_group_id
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.message.chat_id
    target_group_id = chat_id # አውቶማቲክ ሙዚቃ የሚለቀቅበት ግሩፕ ይያዛል
    
    custom_text = custom_welcomes.get(chat_id)

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        name = member.first_name
        
        if custom_text:
            welcome_msg = custom_text.replace("{name}", name)
        else:
            welcome_msg = f"እንኳን ደህና መጣህ/ሽ {name} ወደ ግሩፓችን! 🎉"
            
        await update.message.reply_text(welcome_msg)

# 5. ሊንክ እና ስድብ መቆጣጠር + ከሰዎች ጋር እንደ ሰው ማውራት (Chatting)
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['creator', 'administrator']
    except Exception:
        is_admin = False

    # ሊንክ ሲላክ ያለ ማሳሰቢያ ወዲያውኑ ማጥፋት
    if not is_admin and re.search(URL_PATTERN, text, re.IGNORECASE):
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ስድብ መቆጣጠር
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

    # ቦቱ ሲጠቀስ (Mention) ወይም መልስ ሲሰጠው ልክ እንደ ሰው ማውራት
    if context.bot.username and f"@{context.bot.username}".lower() in text.lower() or message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        await message.reply_text(f"እነሆኝ አልኩኝ! 🤖 ከእርስዎ ጋር እያወራሁ ነው። ምን እንዲረዳዎት ይፈልጋሉ?")

# 6. በሰዓት መርሐ-ግብር (Schedule) ሙዚቃ ወይም መረጃ በራስ-ሰር የሚለቀቅበት ሉፕ
async def scheduled_poster(application):
    await asyncio.sleep(15) # ቦቱ ሲጀመር ትንሽ ይጠብቃል
    while True:
        try:
            if target_group_id:
                # እዚህ ጋር በተባለው ሰዓት ሙዚቃ ወይም ፖስት ይለቀቃል
                await application.bot.send_message(
                    chat_id=target_group_id, 
                    text="🎵 **የሰዓቱ ምርጥ ሙዚቃ/መረጃ ሰዓት ደርሷል!**\nእባክዎ ይደሰቱበት 🎧"
                )
        except Exception:
            pass
        await asyncio.sleep(14400) # በየ 4 ሰዓቱ (በሰከንድ ተሰልቶ)

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()

    # ሀንድለሮች
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ዘመናዊው Maya Ultimate Bot በሰላም ተጀምሯል...")
    
    # አውቶማቲክ ሰዓት ቆጣሪ ማስጀመሪያ
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_poster(application))

    application.run_polling()

if __name__ == "__main__":
    main()
