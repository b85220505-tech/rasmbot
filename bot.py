import logging
import os
from io import BytesIO
from PIL import Image
import imagehash
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# {chat_id: [ (phash_obj, message_id, file_id) ]}
chat_photo_hashes: dict = {}

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

THRESHOLD = 8


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men takroriy rasmlarni topuvchi botman.\n\n"
        "📸 Menga rasm yuboring — men avval yuborilgan o'xshash rasmlarni topib beraman.\n\n"
        "🔍 Buyruqlar:\n"
        "/start — Botni qayta ishga tushirish\n"
        "/stats — Saqlangan rasmlar statistikasi\n"
        "/clear — Barcha rasmlarni tozalash"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    count = len(chat_photo_hashes.get(chat_id, []))
    await update.message.reply_text(f"📊 Bu chatda {count} ta noyob rasm saqlangan.")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_photo_hashes[chat_id] = []
    await update.message.reply_text("🗑️ Barcha rasmlar tozalandi.")


def compute_phash(image_bytes: bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    return imagehash.phash(img, hash_size=16)


async def process_image(image_bytes: bytes, message, chat_id: int, new_file_id: str):
    try:
        new_hash = compute_phash(image_bytes)
    except Exception as e:
        logger.error(f"Hash xatosi: {e}")
        await message.reply_text("❌ Rasmni qayta ishlashda xato yuz berdi.")
        return

    if chat_id not in chat_photo_hashes:
        chat_photo_hashes[chat_id] = []

    saved_list = chat_photo_hashes[chat_id]
    duplicates = []

    for saved_hash, saved_msg_id, saved_file_id in saved_list:
        dist = new_hash - saved_hash
        if dist <= THRESHOLD:
            if dist == 0:
                label = "🔴 Aynan bir xil"
                similarity = 100
            elif dist <= 4:
                label = "🟡 Juda o'xshash"
                similarity = 95 - dist * 2
            else:
                label = "🟠 O'xshash"
                similarity = 85 - dist * 2
            duplicates.append((saved_msg_id, saved_file_id, dist, label, similarity))

    if duplicates:
        duplicates.sort(key=lambda x: x[2])

        # Har bir takroriy rasmni ko'rsat
        for msg_id, file_id, dist, label, similarity in duplicates[:3]:
            caption = (
                f"{label}\n"
                f"📊 O'xshashlik: ~{similarity}%\n"
                f"📎 Xabar raqami: #{msg_id}\n\n"
                f"⬆️ Mana avval yuborilgan rasm!"
            )
            try:
                # Rasmni qayta yuborish
                await message.reply_photo(
                    photo=file_id,
                    caption=caption
                )
            except Exception as e:
                logger.error(f"Rasmni yuborishda xato: {e}")
                # Agar rasm topilmasa, faqat matn yuborish
                await message.reply_text(
                    f"⚠️ *Takroriy rasm topildi!*\n\n"
                    f"{label} — o'xshashlik: ~{similarity}%\n"
                    f"📎 Xabar raqami: #{msg_id}",
                    parse_mode="Markdown"
                )
    else:
        await message.reply_text("✅ Bu rasm yangi! Takroriy topilmadi.")

    # Yangi rasmni saqlash
    saved_list.append((new_hash, message.message_id, new_file_id))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message
    photo = message.photo[-1]

    try:
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())
    except Exception as e:
        logger.error(f"Yuklab olish xatosi: {e}")
        await message.reply_text("❌ Rasmni yuklab olishda xato yuz berdi.")
        return

    await process_image(image_bytes, message, chat_id, photo.file_id)


async def handle_document_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        return

    chat_id = update.effective_chat.id
    message = update.message

    try:
        file = await context.bot.get_file(doc.file_id)
        image_bytes = bytes(await file.download_as_bytearray())
    except Exception as e:
        logger.error(f"Yuklab olish xatosi: {e}")
        await message.reply_text("❌ Faylni yuklab olishda xato yuz berdi.")
        return

    await process_image(image_bytes, message, chat_id, doc.file_id)


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Xato: BOT_TOKEN o'rnatilmagan!")
        print("   CMD da yozing: set BOT_TOKEN=sizning_tokeningiz")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document_photo))

    print("🤖 Bot ishga tushdi! To'xtatish uchun Ctrl+C bosing.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
