import os
import re
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Maya Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_web.run(host="0.0.0.0", port=port)

BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue
        name = member.first_name
        await update.message.reply_text(f"እንኳን ደህና መጣህ/ሽ {name} ወደ ግሩፓችን! 👋")

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

    if not is_admin and re.search(URL_PATTERN, text, re.IGNORECASE):
        try:
            await message.delete()
            await context.bot.send_message(chat_id=chat_id, text="⚠️ ከኦነር/አድሚን ውጪ ሊንክ መላክ የተከለከለ ነው!")
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
                    await context.bot.send_message(chat_id=chat_id, text="🚫 ያልተገባ ቃል በመጠቀሙ/ሟ መልዕክት እንዳይልክ ተገድቧል!")
                except Exception:
                    pass
                break

def main():
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()

    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ቦቱ በሰላም ተጀምሯል...")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
