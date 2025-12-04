import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import threading
import time

# ←←← YOUR BOT TOKEN ←←←
TOKEN = "7738640276:AAH4lWc0_Qq0_Su2hvhhpXFT7LfpyXzF1V8"
bot = telebot.TeleBot(TOKEN)

# Temporary storage: message_id → url (auto cleanup after 10 minutes)
URL_STORAGE = {}
STORAGE_TIMEOUT = 600  # 10 minutes

if not os.path.exists('downloads'):
    os.makedirs('downloads')

def cleanup_storage():
    while True:
        time.sleep(60)
        now = time.time()
        to_remove = [k for k, v in URL_STORAGE.items() if now - v[1] > STORAGE_TIMEOUT]
        for k in to_remove:
            URL_STORAGE.pop(k, None)

# Start cleanup thread
threading.Thread(target=cleanup_storage, daemon=True).start()

def get_ydl_opts(format_type, msg_id):
    if format_type == "audio_best":
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'downloads/{msg_id}_audio.%(ext)s',
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
            'outtmpl': f'downloads/{msg_id}_audio_fast.%(ext)s',
            'quiet': True,
        }
    else:  # video
        return {
            'format': 'best[height<=720]/best',
            'outtmpl': f'downloads/{msg_id}_video.%(ext)s',
            'quiet': True,
        }

def download_and_send(url, message, format_type):
    chat_id = message.chat.id
    msg_id = message.message_id

    try:
        opts = get_ydl_opts(format_type, msg_id)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get('title', 'Instagram Reel')
        duration = info.get('duration', 0)

        # Send Audio
        if format_type.startswith("audio"):
            pattern = f"{msg_id}_audio"
            filename = None
            for f in os.listdir('downloads'):
                if pattern in f and f.endswith('.mp3'):
                    filename = f"downloads/{f}"
                    break

            if filename and os.path.exists(filename):
                with open(filename, 'rb') as audio:
                    bot.send_audio(
                        chat_id, audio,
                        title=title,
                        caption=f"{title}\n\nBot by @YourChannel",
                        reply_to_message_id=message.message_id
                    )
                os.remove(filename)

        # Send Video
        else:
            filename = None
            for f in os.listdir('downloads'):
                if f.startswith(f"{msg_id}_video"):
                    filename = f"downloads/{f}"
                    break

            if filename and os.path.getsize(filename) < 50 * 1024 * 1024:
                with open(filename, 'rb') as video:
                    bot.send_video(
                        chat_id, video,
                        caption=f"{title}\n\nBot by @YourChannel",
                        supports_streaming=True,
                        reply_to_message_id=message.message_id
                    )
                os.remove(filename)
            else:
                bot.send_message(chat_id, "Video 50MB se bada hai, audio bhej raha hoon...")
                # Fallback audio
                opts = get_ydl_opts("audio_best", msg_id)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
                for f in os.listdir('downloads'):
                    if f.startswith(f"{msg_id}_audio") and f.endswith('.mp3'):
                        with open(f"downloads/{f}", 'rb') as audio:
                            bot.send_audio(chat_id, audio, title=title)
                        os.remove(f"downloads/{f}")
                        break

        # Final cleanup
        for f in os.listdir('downloads'):
            if str(msg_id) in f):
                try:
                    os.remove(f"downloads/{f}")
                except:
                    pass

    except Exception as e:
        bot.send_message(chat_id, f"Error ho gaya 😭\n{e}\n\nPublic reel ka link bhejo!")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, """
*Instagram Reel Downloader Bot*

Mujhe public Instagram Reel/Post ka link bhejo

Main tumhe 3 options dunga:
• Audio (Fast)
• Audio (Best Quality) 
• Video (720p)

Bas link daalo aur choose karo!
    """, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_links(message):
    text = message.text.strip()
    if ("instagram.com" in text or "instagr.am" in text) and ("/reel/" in text or "/p/" in text or "/tv/" in text):
        # Store URL with timestamp
        URL_STORAGE[message.message_id] = (text, time.time())

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Audio (Fast)", callback_data=f"audio_fast|{message.message_id}"),
            InlineKeyboardButton("Audio (Best Quality)", callback_data=f"audio_best|{message.message_id}"),
            InlineKeyboardButton("Full Video (720p)", callback_data=f"video|{message.message_id}"),
        )
        bot.reply_to(message, "Kya download karna hai? 👇", reply_markup=markup)
    else:
        bot.reply_to(message, "Bhai sirf public Instagram reel/post ka link bhejo")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        data = call.data.split("|")
        format_type = data[0]
        orig_msg_id = int(data[1])

        if orig_msg_id not in URL_STORAGE:
            bot.answer_callback_query(call.id, "Link expire ho gaya, naya bhejo", show_alert=True)
            return

        url, _ = URL_STORAGE.pop(orig_msg_id)  # remove after use karne ke baad

        bot.answer_callback_query(call.id, "Download start ho gaya...")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Download + upload ho raha hai... 10-30 sec lag sakta hai"
        )

        # Run in background
        threading.Thread(
            target=download_and_send,
            args=(url, call.message.reply_to_message or call.message, format_type),
            daemon=True
        ).start()

    except Exception as e:
        bot.answer_callback_query(call.id, "Error ho gaya!", show_alert=True)
        print("Callback error:", e)

print("Bot is running...")
bot.infinity_polling()
