import logging
import os
import json
import asyncio
import subprocess
import tempfile
from io import BytesIO
from PIL import Image
import imagehash
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8974612126:AAE8aDfI4R03WBb-ZpKbbXTfwLMMiz_i6EU")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
THRESHOLD = 8
DATA_FILE = "bot_data.json"

album_buffer = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}, {}, {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        photo_hashes = {}
        for chat_id, entries in data.get("photo_hashes", {}).items():
            photo_hashes[int(chat_id)] = [
                (imagehash.hex_to_hash(e[0]), e[1], e[2], e[3], e[4], e[5])
                for e in entries
            ]
        duplicates = {}
        for chat_id, entries in data.get("duplicates", {}).items():
            duplicates[int(chat_id)] = entries
        current_dates = {}
        for chat_id, date in data.get("current_dates", {}).items():
            current_dates[int(chat_id)] = date
        return photo_hashes, duplicates, current_dates
    except Exception as e:
        logger.error(f"Yuklashda xato: {e}")
        return {}, {}, {}

def save_data(photo_hashes, duplicates, current_dates):
    try:
        serializable_hashes = {}
        for chat_id, entries in photo_hashes.items():
            serializable_hashes[str(chat_id)] = [
                (str(e[0]), e[1], e[2], e[3], e[4], e[5])
                for e in entries
            ]
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "photo_hashes": serializable_hashes,
                "duplicates": {str(k): v for k, v in duplicates.items()},
                "current_dates": {str(k): v for k, v in current_dates.items()}
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Saqlashda xato: {e}")

chat_photo_hashes, chat_duplicates, chat_current_dates = load_data()

def is_date_format(text: str) -> bool:
    import re
    return bool(re.match(r"^\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}$", text.strip()))

def compute_phash(image_bytes: bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    return imagehash.phash(img, hash_size=16)

def compute_video_hash(video_bytes: bytes):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_vid:
            tmp_vid.write(video_bytes)
            tmp_vid_path = tmp_vid.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            tmp_img_path = tmp_img.name
        result = subprocess.run([
            "ffmpeg", "-y", "-i", tmp_vid_path,
            "-vframes", "1", "-q:v", "2", tmp_img_path
        ], capture_output=True, timeout=30)
        if result.returncode != 0:
            return None
        with open(tmp_img_path, "rb") as f:
            frame_bytes = f.read()
        return compute_phash(frame_bytes)
    except Exception as e:
        logger.error(f"Video hash xatosi: {e}")
        return None
    finally:
        try:
            os.unlink(tmp_vid_path)
            os.unlink(tmp_img_path)
        except:
            pass

def get_username(message) -> str:
    user = message.from_user
    if not user:
        return "Noma'lum"
    if user.username:
        return f"@{user.username}"
    return user.full_name or "Noma'lum"

async def notify_admin(context, caption: str, file_id: str = None, media_type: str = "photo", chat_id: int = None, chat_title: str = None):
    if not ADMIN_ID:
        logger.warning("ADMIN_ID o'rnatilmagan!")
        return
    group_info = f"\n\n📍 Guruh: {chat_title or chat_id}" if chat_id else ""
    full_caption = caption + group_info
    try:
        if file_id and media_type == "video":
            await context.bot.send_video(chat_id=ADMIN_ID, video=file_id, caption=full_caption, parse_mode="Markdown")
        elif file_id:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=full_caption, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=full_caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin ga xabar yuborishda xato: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men takroriy media fayllarni topuvchi botman.\n\n"
        "📅 Ishlash tartibi:\n"
        "1. Sanani yozing: `1.06.2026`\n"
        "2. Rasm yoki video yuboring\n"
        "3. Tugatish uchun: `stop`\n\n"
        "/report — Barcha takroriylar\n"
        "/stats  — Statistika\n"
        "/clear  — Tozalash\n"
        "/myid   — Mening ID'im",
        parse_mode="Markdown"
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Sizning ID'ingiz: `{user_id}`", parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    total = len(chat_photo_hashes.get(chat_id, []))
    dups = len(chat_duplicates.get(chat_id, []))
    current_date = chat_current_dates.get(chat_id)
    date_text = f"📅 Joriy sana: *{current_date}*\n" if current_date else "📅 Sana kiritilmagan\n"
    await update.message.reply_text(
        f"{date_text}📊 Jami: *{total}* ta\n⚠️ Takroriylar: *{dups}* ta",
        parse_mode="Markdown"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_photo_hashes[chat_id] = []
    chat_duplicates[chat_id] = []
    chat_current_dates[chat_id] = None
    save_data(chat_photo_hashes, chat_duplicates, chat_current_dates)
    await update.message.reply_text("🗑️ Barcha ma'lumotlar tozalandi.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    dups = chat_duplicates.get(chat_id, [])
    if not dups:
        await update.message.reply_text("✅ Hozircha takroriy topilmadi.")
        return
    await update.message.reply_text(f"📋 *Takroriy media* — jami {len(dups)} ta:", parse_mode="Markdown")
    for i, entry in enumerate(dups, 1):
        orig_msg_id, orig_user, orig_date, dup_msg_id, dup_user, dup_date, file_id, media_type = entry
        icon = "🎥" if media_type == "video" else "🖼"
        caption = (
            f"🔁 *{i}-takroriy {icon}*\n"
            f"📌 Birinchi: {orig_user} — {orig_date}\n"
            f"♻️ Qayta: {dup_user} — {dup_date}"
        )
        try:
            if media_type == "video":
                await update.message.reply_video(video=file_id, caption=caption, parse_mode="Markdown")
            else:
                await update.message.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(caption, parse_mode="Markdown")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    if text.lower() == "stop":
        current_date = chat_current_dates.get(chat_id)
        if current_date:
            chat_current_dates[chat_id] = None
            save_data(chat_photo_hashes, chat_duplicates, chat_current_dates)
            await update.message.reply_text(f"⏹️ *{current_date}* sessiyasi tugatildi.", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Faol sessiya yo'q.")
        return
    if is_date_format(text):
        chat_current_dates[chat_id] = text
        save_data(chat_photo_hashes, chat_duplicates, chat_current_dates)
        total = len(chat_photo_hashes.get(chat_id, []))
        await update.message.reply_text(
            f"📅 Sana belgilandi: *{text}*\nBazada {total} ta media bor.",
            parse_mode="Markdown"
        )

async def check_and_save(media_hash, file_id, message, chat_id, current_date, context, media_type="photo"):
    if chat_id not in chat_photo_hashes:
        chat_photo_hashes[chat_id] = []
    if chat_id not in chat_duplicates:
        chat_duplicates[chat_id] = []
    saved_list = chat_photo_hashes[chat_id]
    sender = get_username(message)
    best_match = None
    for saved_hash, saved_msg_id, saved_file_id, saved_user, saved_date, saved_type in saved_list:
        dist = media_hash - saved_hash
        if dist <= THRESHOLD:
            if best_match is None or dist < best_match[0]:
                best_match = (dist, saved_msg_id, saved_file_id, saved_user, saved_date, saved_type)
    is_duplicate = False
    if best_match:
        dist, orig_msg_id, orig_file_id, orig_user, orig_date, orig_type = best_match
        if dist == 0:
            label = "🔴 Aynan bir xil"
        elif dist <= 4:
            label = "🟡 Juda o'xshash"
        else:
            label = "🟠 O'xshash"
        icon = "🎥" if media_type == "video" else "🖼"
        chat = message.chat
        chat_title = chat.title if chat.title else str(chat_id)
        if chat.username:
            msg_link = f"https://t.me/{chat.username}/{message.message_id}"
            orig_link = f"https://t.me/{chat.username}/{orig_msg_id}"
        else:
            msg_link = f"(xabar #{message.message_id})"
            orig_link = f"(xabar #{orig_msg_id})"
        caption = (
            f"⚠️ *Takroriy {icon} topildi!*\n{label}\n\n"
            f"📌 Birinchi yuborgan: {orig_user}\n"
            f"   📅 Sana: *{orig_date}*\n"
            f"   🔗 {orig_link}\n\n"
            f"♻️ Qayta yuborgan: {sender}\n"
            f"   📅 Sana: *{current_date}*\n"
            f"   🔗 {msg_link}"
        )
        await notify_admin(context, caption, file_id=orig_file_id, media_type=media_type, chat_id=chat_id, chat_title=chat_title)
        chat_duplicates[chat_id].append(
            (orig_msg_id, orig_user, orig_date, message.message_id, sender, current_date, orig_file_id, media_type)
        )
        is_duplicate = True
    saved_list.append((media_hash, message.message_id, file_id, sender, current_date, media_type))
    save_data(chat_photo_hashes, chat_duplicates, chat_current_dates)
    return is_duplicate

async def process_single_photo(message, chat_id, context):
    current_date = chat_current_dates.get(chat_id)
    if not current_date:
        return
    photo = message.photo[-1]
    try:
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())
        media_hash = compute_phash(image_bytes)
    except Exception as e:
        logger.error(e)
        return
    await check_and_save(media_hash, photo.file_id, message, chat_id, current_date, context, "photo")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = update.effective_chat.id
    if message.media_group_id:
        mgid = message.media_group_id
        if chat_id not in album_buffer:
            album_buffer[chat_id] = {}
        if mgid not in album_buffer[chat_id]:
            album_buffer[chat_id][mgid] = []
            asyncio.create_task(process_album(chat_id, mgid, context))
        album_buffer[chat_id][mgid].append(message)
        return
    await process_single_photo(message, chat_id, context)

async def process_album(chat_id: int, media_group_id: str, context):
    await asyncio.sleep(1.5)
    messages = album_buffer.get(chat_id, {}).pop(media_group_id, [])
    if not messages:
        return
    current_date = chat_current_dates.get(chat_id)
    if not current_date:
        return
    for message in messages:
        if not message.photo:
            continue
        photo = message.photo[-1]
        try:
            file = await context.bot.get_file(photo.file_id)
            image_bytes = bytes(await file.download_as_bytearray())
            media_hash = compute_phash(image_bytes)
        except Exception as e:
            logger.error(e)
            continue
        await check_and_save(media_hash, photo.file_id, message, chat_id, current_date, context, "photo")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = update.effective_chat.id
    current_date = chat_current_dates.get(chat_id)
    if not current_date:
        return
    video = message.video or message.video_note
    if not video:
        return
    try:
        file = await context.bot.get_file(video.file_id)
        video_bytes = bytes(await file.download_as_bytearray())
    except Exception as e:
        logger.error(e)
        return
    media_hash = compute_video_hash(video_bytes)
    if media_hash is None:
        return
    await check_and_save(media_hash, video.file_id, message, chat_id, current_date, context, "video")

async def handle_document_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type:
        return
    current_date = chat_current_dates.get(update.effective_chat.id)
    if not current_date:
        return
    if doc.mime_type.startswith("image/"):
        try:
            file = await context.bot.get_file(doc.file_id)
            image_bytes = bytes(await file.download_as_bytearray())
            media_hash = compute_phash(image_bytes)
        except Exception as e:
            logger.error(e)
            return
        await check_and_save(media_hash, doc.file_id, update.message, update.effective_chat.id, current_date, context, "photo")
    elif doc.mime_type.startswith("video/"):
        try:
            file = await context.bot.get_file(doc.file_id)
            video_bytes = bytes(await file.download_as_bytearray())
        except Exception as e:
            logger.error(e)
            return
        media_hash = compute_video_hash(video_bytes)
        if media_hash is None:
            return
        await check_and_save(media_hash, doc.file_id, update.message, update.effective_chat.id, current_date, context, "video")

def main():
    print(f"✅ Admin ID: {ADMIN_ID}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.VIDEO_NOTE, handle_video))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_photo))
    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
