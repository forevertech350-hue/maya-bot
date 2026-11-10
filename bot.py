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
    return "Maya Booster Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

custom_welcomes = {}
target_group_id = None
post_queue = [] 

BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("⚙️ Your groups"), KeyboardButton("🎈 Add to group")],
        [KeyboardButton("🔶 help"), KeyboardButton("😊 Support")],
        [KeyboardButton("🔶 rules"), KeyboardButton("🚩 Language")],
        [KeyboardButton("🌐 Bot translation"), KeyboardButton("💰 donate")],
        [KeyboardButton("🔧 New channel management bot")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if update.message:
        bot_username = context.bot.username
        await update.message.reply_text(
            f"Hi, I'm Maya Booster, to use me I have to be added to your group as admin :)\n🌹\n\nSupport :\nhttps://t.me/CleanRobotHelp\n🌿",
            reply_markup=reply_markup
        )

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
        asyncio.create_task(delete_after_delay(sent_msg, 60))

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

async def handle_buttons_and_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id

    if text == "⚙️ Your groups":
        await message.reply_text("📋 የእርስዎ ግሩፖች ዝርዝር በዚህ መልኩ ይቀርባል:")
        return
    elif text == "🎈 Add to group":
        bot_username = context.bot.username
        await message.reply_text(f"ቦቱን ወደ ግሩፕዎ ለመጨመር ይህንን ሊንክ ይጠቀሙ:\nhttps://t.me/{bot_username}?startgroup=true")
        return
    elif text == "🔶 help" or text == "😊 Support":
        await message.reply_text("SUPPORT:\nhttps://t.me/CleanRobotHelp")
        return
    elif text == "🔶 rules":
        await message.reply_text("📜 የግሩፕ ደንቦች:\n1. ሊንክ መላክ የተከለከለ ነው (በጸጥታ ይጠፋል)\n2. ስድብ እና ጸያፍ ቃላት ማጥፋት የተከለከለ ነው")
        return
    elif text == "🚩 Language":
        keyboard = [
            [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        await message.reply_text("እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Choose your language:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif text == "💰 donate":
        await message.reply_text("🙏 ስለለገሱ እናመሰግናለን!")
        return
    elif text == "🌐 Bot translation":
        await message.reply_text("🌐 የቦቱን ቋንቋዎች ለማስተካከል ይደውሉልን።")
        return
    elif text == "🔧 New channel management bot":
        await message.reply_text("🤖 አዲስ የቻናል ማኔጅመንት ቦት በቅርቡ ይመጣል።")
        return

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

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "lang_am":
        await query.edit_message_text(text="✅ ቋንቋ ወደ **አማርኛ** ተቀይሯል።")
    elif query.data == "lang_en":
        await query.edit_message_text(text="✅ Language changed to **English**.")

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("addpost", add_post))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons_and_messages))

    print("ቦቱ በሰላም ተጀምሯል...")
    application.run_polling()

if __name__ == "__main__":
    main()
