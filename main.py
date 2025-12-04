import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import threading

# ←←← APNA BOT TOKEN YAHAN DAALO ←←←
bot = telebot.TeleBot(TOKEN)

# Folders
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# Common yt-dlp options
def get_ydl_opts(format_type, msg_id):
    if format_type == "audio_best":
        return {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'downloads/{msg_id}_audio',
            'quiet': True,
        }
    elif format_type == "audio_fast":
        return {
            'format': 'worstaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': f'downloads/{msg_id}_audio_fast',
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

        if format_type in ["audio_best", "audio_fast"]:
            filename = f"downloads/{msg_id}_audio.mp3" if format_type == "audio_best" else f"downloads/{msg_id}_audio_fast.mp3"
            with open(filename, 'rb') as audio:
                bot.send_audio(
                    chat_id,
                    audio,
                    title=title,
                    caption=f"🎧 {title}\n\nBot by @YourChannel",
                    reply_to_message_id=message.message_id
                )
            os.remove(filename)

        else:  # video
            filename = None
            for file in os.listdir('downloads'):
                if file.startswith(f"{msg_id}_video"):
                    filename = f"downloads/{file}"
                    break
            if filename and os.path.getsize(filename) < 50 * 1024 * 1024:  # <50MB
                with open(filename, 'rb') as video:
                    bot.send_video(
                        chat_id,
                        video,
                        caption=f"🎬 {title}\n\nBot by @YourChannel",
                        supports_streaming=True,
                        reply_to_message_id=message.message_id
                    )
            else:
                bot.send_message(chat_id, "Video 50MB se bada hai, sirf audio bhej raha hoon...")
                # fallback to audio
                opts = get_ydl_opts("audio_best", msg_id)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
                with open(f"downloads/{msg_id}_audio.mp3", 'rb') as audio:
                    bot.send_audio(chat_id, audio, title=title)
                os.remove(f"downloads/{msg_id}_audio.mp3")
            if filename:
                os.remove(filename)

        # Clean up any leftover files
        for f in os.listdir('downloads'):
            if str(msg_id) in f:
                try: os.remove(f"downloads/{f}")
                except: pass

    except Exception as e:
        bot.send_message(chat_id, f"Galti ho gayi 😭\n{e}\n\nPublic Reel ka link bhejo!")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, """
🚀 *Instagram Reel Downloader Bot*

Mujhe koi bhi Instagram Reel ka link bhejo → Main button dikhaunga:

• Audio (Fast)  
• Audio (Best Quality)  
• Full Video (720p)

Bas link bhejo aur choose karo! 🔥
    """, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_links(message):
    text = message.text
    if "instagram.com" in text or "instagr.am" in text:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🎧 Audio (Fast)", callback_data=f"audio_fast|{message.message_id}|{text}"),
            InlineKeyboardButton("🎵 Audio (Best Quality)", callback_data=f"audio_best|{message.message_id}|{text}"),
            InlineKeyboardButton("🎬 Full Video (720p)", callback_data=f"video|{message.message_id}|{text}"),
        )
        bot.reply_to(message, "Choose karo kya chahiye 👇", reply_markup=markup)
    else:
        bot.reply_to(message, "Bhai Instagram ka link bhejo na 😅")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        data = call.data.split("|")
        format_type = data[0]
        orig_msg_id = int(data[1])
        url = data[2]

        bot.answer_callback_query(call.id, "Download shuru kar diya ⏳")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⏳ Download ho raha hai... 5-15 sec lagega"
        )

        # Background mein download karega
        threading.Thread(target=download_and_send, args=(url, call.message, format_type)).start()

    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")

print("Bot chal gaya! 🚀")
bot.infinity_polling()
