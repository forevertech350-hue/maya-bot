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
    return "Maya Ultimate Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

user_languages = {}
custom_welcomes = {}
target_group_id = None
post_queue = [] # አድሚኖች የጨመሯቸው ፖስቶች የሚቀመጡበት ዝርዝር

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

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ['creator', 'administrator']:
            return
    except Exception:
        return

    text_args = " ".join(context.args)
    if not text_args:
        await message.reply_text("⚠️ እባክዎ መልእክት አብረው ይጻፉ። ምሳሌ: `/setwelcome እንኳን ደህና መጡ {name}`", parse_mode="Markdown")
        return

    custom_welcomes[chat_id] = text_args
    await message.reply_text("✅ የእንኳን ደህና መጣችሁ መልእክት ተስተካክሏል!")

# መልእክት ከ 1 ደቂቃ በኋላ በራሱ እንዲጠፋ የሚያደርግ ረዳት ተግባር
async def delete_after_delay(message, delay=60):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global target_group_id
    if not update.message or not update.message.new_chat_members:
        return
    
    chat_id = update.message.chat_id
    target_group_id = chat_id
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
        # መልእክቱ ከ 60 ሰከንድ (1 ደቂቃ) በኋላ በራሱ እንዲጠፋ ይደረጋል
        asyncio.create_task(delete_after_delay(sent_msg, 60))

# አድሚኖች ፖስት እንዲያስገቡ የሚረዳ ትዕዛዝ (/addpost)
async def add_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status not in ['creator', 'administrator']:
            await message.reply_text("⚠️ ይህንን ትዕዛዝ መጠቀም የሚችሉት አድሚኖች ብቻ ናቸው!")
            return
    except Exception:
        pass

    post_text = " ".join(context.args)
    if not post_text:
        await message.reply_text("⚠️ እባክዎ የሚለቀቀውን ጽሁፍ አብረው ይጻፉ።\nምሳሌ: `/addpost የዛሬው ጠቃሚ መረጃ...`", parse_mode="Markdown")
        return

    post_queue.append(post_text)
    await message.reply_text("✅ ፖስቱ በተሳካ ሁኔታ ተመዝግቧል! በቅርቡ ወደ ግሩፕ ይለቀቃል።")

# በሰዓቱ አውቶማቲክ ፖስቶችን የሚለቅ ሲስተም
async def scheduled_poster(application):
    await asyncio.sleep(20)
    while True:
        try:
            if target_group_id and post_queue:
                current_post = post_queue.pop(0) # የመጀመሪያውን ፖስት ማውጣት
                await application.bot.send_message(chat_id=target_group_id, text=f"📢 **አዲስ ማስታወቂያ/ፖስት**\n\n{current_post}", parse_mode="Markdown")
        except Exception:
            pass
        await asyncio.sleep(7200) # በየ 2 ሰዓቱ አንድ ፖስት ይለቀቃል (ማስተካከል ይቻላል)

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

    # ሊንክ ሲላክ በጸጥታ ማጥፋት
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

    # ከሰዎች ጋር ማውራት (Mention ሲደረግ ወይም ሪፕላይ ሲሰጥ)
    if context.bot.username and f"@{context.bot.username}".lower() in text.lower() or message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        await message.reply_text("እነሆኝ አልኩኝ! 🤖 ከእርስዎ ጋር እያወራሁ ነው። ምን እንዲረዳዎት ይፈልጋሉ?")

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("addpost", add_post))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ቦቱ በሰላም ተጀምሯል...")
    
    # አውቶማቲክ ፖስት ማከፋፈያ ማስጀመሪያ
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_poster(application))

    application.run_polling()

if __name__ == "__main__":
    main()
