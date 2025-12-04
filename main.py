import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import threading
import time

# ←←← YOUR BOT TOKEN ←←←
TOKEN = "7738640276:AAH4lWc0_Qq0_Su2hvhhpXFT7LfpyXzF1V8"
bot = telebot.TeleBot(TOKEN)

# Temporary storage: message_id → (url, timestamp)
URL_STORAGE = {}
STORAGE_TIMEOUT = 600  # 10 minutes

# Create downloads folder
if not os.path.exists('downloads'):
    os.makedirs('downloads')

def cleanup_storage():
    while True:
        time.sleep(60)
        now = time.time()
        expired = [k for k, v in URL_STORAGE.items() if now - v[1] > STORAGE_TIMEOUT]
        for k in expired:
            URL_STORAGE.pop(k, None)

# Start cleanup thread
threading.Thread(target=cleanup_storage, daemon=True).start()

def get_ydl_opts(format_type, msg_id):
    output_template = f'downloads/{msg_id}_%(title).50s.%(ext)s'  # Safe filename

    if format_type == "audio_best":
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
    elif format_type == "audio_fast":
        return {
            'format': 'worstaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': output_template,
            'quiet': True,
        }
    else:  # video
        return {
            'format': 'best[height<=720]/best',
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'quiet': True,
        }

def download_and_send(url, message, format_type):
    chat_id = message.chat.id
    reply_to_id = message.message_id

    try:
        # Edit status
        status_msg = bot.send_message(chat_id, "Downloading... ⏳", reply_to_message_id=reply_to_id)
        
        opts = get_ydl_opts(format_type, reply_to_id)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Instagram Reel')
            duration = info.get('duration', 0) or 0
            thumbnail = info.get('thumbnail')

        # Find downloaded file
        downloaded_file = None
        for file in os.listdir('downloads'):
            if str(reply_to_id) in file:
                downloaded_file = os.path.join('downloads', file)
                break

        if not downloaded_file or not os.path.exists(downloaded_file):
            bot.edit_message_text("File nahi mila after download!", chat_id, status_msg.message_id)
            return

        file_size = os.path.getsize(downloaded_file) / (1024 * 1024)  # MB

        # Send Audio
        if format_type.startswith("audio"):
            with open(downloaded_file, 'rb') as audio:
                bot.edit_message_text("Uploading audio... 🎵", chat_id, status_msg.message_id)
                bot.send_audio(
                    chat_id=chat_id,
                    audio=audio,
                    title=title,
                    performer="Instagram @reel",
                    duration=duration,
                    thumb=thumbnail,
                    caption=f"{title}\n\nDownloaded by @YourBotUsername",
                    reply_to_message_id=reply_to_id
                )
        
        # Send Video (if < 50MB)
        elif file_size < 49:  # Telegram limit ~50MB
            with open(downloaded_file, 'rb') as video:
                bot.edit_message_text("Uploading video... 🎥", chat_id, status_msg.message_id)
                bot.send_video(
                    chat_id=chat_id,
                    video=video,
                    duration=duration,
                    caption=f"{title}\n\nDownloaded by @YourBotUsername",
                    supports_streaming=True,
                    reply_to_message_id=reply_to_id
                )
        else:
            # Video too big → send best audio instead
            bot.edit_message_text("Video 50MB se bada hai! Best audio bhej raha hoon... 🎧", chat_id, status_msg.message_id)
            audio_opts = get_ydl_opts("audio_best", reply_to_id)
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                ydl.download([url])

            # Find new audio file
            audio_file = None
            for f in os.listdir('downloads'):
                if str(reply_to_id) in f and f.endswith('.mp3'):
                    audio_file = os.path.join('downloads', f)
                    break

            if audio_file and os.path.exists(audio_file):
                with open(audio_file, 'rb') as audio:
                    bot.send_audio(
                        chat_id=chat_id,
                        audio=audio,
                        title=title,
                        performer="Instagram",
                        caption=f"{title}\n(Video was too big, sent best audio)\n\n@YourBotUsername",
                        reply_to_message_id=reply_to_id
                    )

        # Final success message
        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        error_text = "Error ho gaya 😭\n\nSirf *public* reel/post ka link bhejo!"
        try:
            bot.edit_message_text(error_text, chat_id, status_msg.message_id if 'status_msg' in locals() else None)
        except:
            bot.send_message(chat_id, error_text)
        print("Error:", e)

    finally:
        # Clean up all files related to this message
        for file in os.listdir('downloads'):
            if file.startswith(str(reply_to_id)) or str(reply_to_id) in file:
                try:
                    os.remove(os.path.join('downloads', file))
                except:
                    pass

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, """
*Instagram Reel Downloader Bot* 🎥

Mujhe public Instagram reel ya post ka link bhejo.

Main tumhe 3 options dunga:
• Fast Audio
• Best Quality Audio
• Full Video (720p)

Bas link paste karo aur choose karo!
    """, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_links(message):
    text = message.text.strip()
    if not text:
        return

    if ("instagram.com" in text or "instagr.am" in text) and ("/reel/" in text or "/p/" in text or "/tv/" in text):
        URL_STORAGE[message.message_id] = (text, time.time())

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Audio Fast", callback_data=f"audio_fast|{message.message_id}"),
            InlineKeyboardButton("Audio Best Quality", callback_data=f"audio_best|{message.message_id}"),
            InlineKeyboardButton("Video 720p", callback_data=f"video|{message.message_id}"),
        )
        bot.reply_to(message, "Format choose karo 👇", reply_markup=markup)
    else:
        bot.reply_to(message, "Bhai sirf *public* Instagram reel/post ka link bhejo!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if '|' not in call.data:
            return
        format_type, orig_msg_id = call.data.split("|", 1)
        orig_msg_id = int(orig_msg_id)

        if orig_msg_id not in URL_STORAGE:
            bot.answer_callback_query(call.id, "Link expire ho gaya! Naya bhejo", show_alert=True)
            return

        url, _ = URL_STORAGE.pop(orig_msg_id)
        bot.answer_callback_query(call.id, "Start ho gaya... ⏳")

        # Use the original message (reply_to_message)
        original_message = call.message.reply_to_message
        if not original_message:
            original_message = call.message

        threading.Thread(
            target=download_and_send,
            args=(url, original_message, format_type),
            daemon=True
        ).start()

        # Optional: Edit button message
        bot.edit_message_text(
            "Processing your request...\n10-40 seconds lagenge ⏳",
            call.message.chat.id,
            call.message.message_id
        )

    except Exception as e:
        bot.answer_callback_query(call.id, "Error!", show_alert=True)
        print("Callback error:", e)

print("Bot is running...")
bot.infinity_polling(none_stop=True, interval=0)