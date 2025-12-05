# bot.py
import os
import instaloader
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Apna Telegram Bot Token yahan daal do (BotFather se)
TOKEN = "7738640276:AAH4lWc0_Qq0_Su2hvhhpXFT7LfpyXzF1V8"   # ← YAHAN APNA TOKEN DAALO

# Instagram login (ek baar daal do, baad mein session save ho jayega)
IG_USERNAME = "zebra.3335447"    # ← Yahan apna IG username
IG_PASSWORD = "S4UR4BHXD"    # ← Yahan password

# Instaloader setup
L = instaloader.Instaloader()

# Pehli baar login karega, baad mein session file use karega
if not os.path.exists("session-" + IG_USERNAME):
    print("Logging in to Instagram...")
    L.login(IG_USERNAME, IG_PASSWORD)
    L.save_session_to_file()
else:
    L.load_session_from_file(IG_USERNAME)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me any Instagram Reel/Post link 😘\n"
        "Main video + audio best quality mein bhej dunga!"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    msg = await update.message.reply_text("Downloading kar raha hoon... ⏳")

    try:
        shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
        if "?" in shortcode:
            shortcode = shortcode.split("?")[0]

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Temporary folder
        os.makedirs("temp", exist_ok=True)

        # Download video (best quality)
        L.download_post(post, target="temp")

        # Find the video file
        for file in os.listdir("temp"):
            if file.endswith(".mp4") and not file.endswith("_thumb.mp4"):
                video_path = os.path.join("temp", file)
                await update.message.reply_video(
                    video=open(video_path, 'rb'),
                    caption=f"@{update.effective_user.username}\n❤️ Done!"
                )
                os.remove(video_path)
                break

        # Clean temp folder
        for f in os.listdir("temp"):
            os.remove(os.path.join("temp", f))

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"Error ho gaya 😭\n{str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("Bot chal gaya! 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
