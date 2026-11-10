import os
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# የቦት Token በቀጥታ እዚህ ተካትቷል
TOKEN = "9002390854:AAGxZZoSu0f4pjDtE2bF7YGwSvlFP--sBqU"

# የተከለከሉ/መጥፎ ቃላት ዝርዝር (እዚህ ጋር የሚፈልጉትን ስድብ ወይም ቃል መጨመር ይችላሉ)
BAD_WORDS = ["ስድብ1", "ስድብ2", "badword1", "badword2"]

# ሊንክ ማወቂያ (Regex Pattern)
URL_PATTERN = r"(https?://[^\s]+|t\.me/[^\s]+|www\.[^\s]+)"

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """አዲስ ሰው ሲቀላቀል ሰላምታ የሚሰጥ"""
    if not update.message or not update.message.new_chat_members:
        return
        
    for member in update.message.new_chat_members:
        # ቦቱ እራሱ ከተጨመረ ችላ እንዲል
        if member.id == context.bot.id:
            continue
        
        name = member.first_name
        welcome_text = f"እንኳን ደህና መጣህ/ሽ {name} ወደ ግሩፓችን! 👋\nእባክህ/ሽ የግሩፑን ህጎች አክብር/ሪ።"
        await update.message.reply_text(welcome_text)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ሊንክ እና መጥፎ ቃላትን መቆጣጠሪያ"""
    message = update.message
    if not message or not message.text:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # መልዕክቱን የላከው አድሚን ወይም ኦነር መሆኑን ማረጋገጥ
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['creator', 'administrator']
    except Exception:
        is_admin = False

    text = message.text

    # 1. ከኦነር/አድሚን ውጪ ሊንክ የላከ ካለ ማጥፋት
    if not is_admin and re.search(URL_PATTERN, text, the_flag := re.IGNORECASE):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ @{message.from_user.username or message.from_user.first_name} ከኦነር/አድሚን ውጪ ሊንክ መላክ የተከለከለ ነው!"
            )
        except Exception as e:
            print(f"Error deleting link message: {e}")
        return

    # 2. መጥፎ ቃላትን ማጣራት እና Restrict ማድረግ (ከአድሚን ውጪ)
    if not is_admin:
        for word in BAD_WORDS:
            if word.lower() in text.lower():
                try:
                    # መልዕክቱን ማጥፋት
                    await message.delete()
                    
                    # አባሉን Restrict ማድረግ (መልዕክት እንዳይልል መከልከል)
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        permissions={"can_send_messages": False}
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚫 @{message.from_user.username or message.from_user.first_name} ያልተገባ ቃል በመጠቀሙ/ሟ መልዕክት እንዳይልክ ተገድቧል!"
                    )
                except Exception as e:
                    print(f"Error restricting user: {e}")
                break

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # አዲስ ሰው ሲገባ ማወቂያ Handler
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    # ማንኛውም የጽሑፍ መልዕክት ሲላክ ማጣሪያ Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))

    print("ቦቱ ሥራ ጀምሯል...")
    app.run_polling()

if __name__ == "__main__":
    main()
