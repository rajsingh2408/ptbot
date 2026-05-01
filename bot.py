import yt_dlp
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_video = {}
user_results = {}

# ---------- GRID MENU ----------
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Search", callback_data="search"),
            InlineKeyboardButton("🎧 Download", callback_data="download")
        ],
        [
            InlineKeyboardButton("🔥 Trending", callback_data="trending"),
            InlineKeyboardButton("🏠 Home", callback_data="home")
        ]
    ])

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 *Media Dashboard*\n\nChoose an option:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ---------- SEARCH ----------
def search_youtube(query):
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        results = ydl.extract_info(f"ytsearch3:{query}", download=False)
    return results['entries']

# ---------- BUTTON HANDLER ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    # HOME
    if data == "home":
        await query.edit_message_text(
            "🏠 Main Menu",
            reply_markup=main_menu()
        )

    # SEARCH
    elif data == "search":
        context.user_data["mode"] = "search"
        await query.edit_message_text("🔍 Type song name:")

    # DOWNLOAD MODE
    elif data == "download":
        context.user_data["mode"] = "download"
        await query.edit_message_text("🎧 Paste YouTube link:")

    # TRENDING
    elif data == "trending":
        context.user_data["mode"] = "search"
        await query.edit_message_text("🔥 Trending Songs:\n(Type anything to refresh list)")

    # SELECT SONG
    elif data.startswith("select_"):
        index = int(data.split("_")[1])
        video = user_results[user_id][index]

        video_id = video.get("id")
        title = video.get("title")

        user_video[user_id] = video_id

        thumb = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎧 Download", callback_data="download_now")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_list")]
        ])

        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=thumb, caption=f"🎵 {title}"),
                reply_markup=keyboard
            )
        except:
            await query.message.reply_photo(photo=thumb, caption=f"🎵 {title}", reply_markup=keyboard)

    # DOWNLOAD BUTTON
    elif data == "download_now":
        video_id = user_video.get(user_id)

        if not video_id:
            await query.answer("No video selected")
            return

        url = f"https://www.youtube.com/watch?v={video_id}"

        await query.answer("Downloading...")

        msg = await query.message.reply_text("⏳ Downloading...")
        asyncio.create_task(download_audio(msg, url))

    # BACK TO LIST
    elif data == "back_to_list":
        results = user_results[user_id]

        keyboard = []
        for i, v in enumerate(results):
            title = v.get("title")
            keyboard.append([
                InlineKeyboardButton(title[:40], callback_data=f"select_{i}")
            ])

        await query.edit_message_text(
            "🔍 Select a song:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ---------- HANDLE TEXT ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    mode = context.user_data.get("mode")

    # SEARCH MODE
    if mode == "search":
        results = search_youtube(update.message.text)
        user_results[user_id] = results

        keyboard = []
        for i, v in enumerate(results):
            title = v.get("title")
            keyboard.append([
                InlineKeyboardButton(title[:40], callback_data=f"select_{i}")
            ])

        await update.message.reply_text(
            "🔍 Select a song:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # DOWNLOAD MODE
    elif mode == "download":
        url = update.message.text
        msg = await update.message.reply_text("⏳ Downloading...")
        asyncio.create_task(download_audio(msg, url))

# ---------- DOWNLOAD ----------
async def download_audio(msg, url):
    try:
        loop = asyncio.get_event_loop()

        def run_download():
            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': '%(id)s.%(ext)s'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get("title")

        file_name, title = await loop.run_in_executor(None, run_download)

        if os.path.getsize(file_name) < 50 * 1024 * 1024:
            await msg.reply_audio(audio=open(file_name, 'rb'), title=title)
        else:
            await msg.reply_text("❌ File too large")

        os.remove(file_name)

    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)}")

# ---------- RUN ----------
app = ApplicationBuilder().token(BOT_TOKEN)\
    .connect_timeout(30)\
    .read_timeout(30)\
    .write_timeout(30)\
    .build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Bot running...")
app.run_polling()
