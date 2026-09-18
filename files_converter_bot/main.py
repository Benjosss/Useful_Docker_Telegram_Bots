import os
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import img2pdf
from pdf2image import convert_from_path
from pdf2docx import Converter

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

def is_authorized(user_id: int) -> bool:
    """Checks if the user is authorized."""
    return user_id == ALLOWED_USER_ID

# --- IMAGE PROCESSING ---

def process_image(input_path: str, output_path: str, action: str):
    """Handles image compression and conversions."""
    with Image.open(input_path) as img:
        if action == "img_compress":
            img = img.convert("RGB")
            img.save(output_path, "JPEG", optimize=True, quality=40)
        elif action == "img_to_jpg":
            img = img.convert("RGB")
            img.save(output_path, "JPEG")
        elif action == "img_to_png":
            img.save(output_path, "PNG")
        elif action == "img_to_ico":
            # Resize for icon if necessary
            img = img.resize((256, 256))
            img.save(output_path, "ICO")

def image_to_pdf(input_path: str, output_path: str):
    with open(output_path, "wb") as f:
        f.write(img2pdf.convert(input_path))

# --- DOCUMENT PROCESSING (PDF/DOCX) ---

def docx_to_pdf(input_path: str, output_dir: str):
    """Uses LibreOffice in headless mode to convert a DOCX file to PDF."""
    cmd = [
        "libreoffice", "--headless", "--convert-to", "pdf",
        input_path, "--outdir", output_dir
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def pdf_to_docx(input_path: str, output_path: str):
    """Converts a PDF file to DOCX using pdf2docx."""
    cv = Converter(input_path)
    cv.convert(output_path, start=0, end=None)
    cv.close()

def pdf_to_images(input_path: str, output_dir: str) -> list[str]:
    """Extracts the first 3 pages of a PDF as images."""
    images = convert_from_path(input_path, first_page=1, last_page=3)
    files = []
    for i, image in enumerate(images):
        out = os.path.join(output_dir, f"page_{i+1}.jpg")
        image.save(out, "JPEG")
        files.append(out)
    return files

# --- VIDEO PROCESSING ---

def process_video(input_path: str, output_path: str, action: str):
    if action == "vid_compress":
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vcodec", "libx264", "-crf", "28", "-preset", "fast", output_path]
    elif action == "vid_to_mp3":
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- TELEGRAM MANAGEMENT ---

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    message = update.message
    file_obj = None

    if message.document:
        file_obj = await message.document.get_file()
        file_name = message.document.file_name or "file"
    elif message.photo:
        file_obj = await message.photo[-1].get_file()
        file_name = "photo.jpg"
    else:
        return

    ext = Path(file_name).suffix.lower()

    context.user_data["file_id"] = file_obj.file_id
    context.user_data["file_name"] = file_name
    context.user_data["ext"] = ext

    buttons = []
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        buttons = [
            [InlineKeyboardButton("🗜️ Compress (JPG)", callback_data="img_compress")],
            [InlineKeyboardButton("🔄 Convert to JPG", callback_data="img_to_jpg"),
             InlineKeyboardButton("🔄 Convert to PNG", callback_data="img_to_png")],
            [InlineKeyboardButton("🔳 Convert to ICO", callback_data="img_to_ico"),
             InlineKeyboardButton("📄 Convert to PDF", callback_data="img_to_pdf")],
        ]
    elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
        buttons = [
            [InlineKeyboardButton("🎬 Compress Video", callback_data="vid_compress")],
            [InlineKeyboardButton("🎵 Extract Audio (MP3)", callback_data="vid_to_mp3")],
        ]
    elif ext == ".pdf":
        buttons = [
            [InlineKeyboardButton("📝 Convert to DOCX", callback_data="pdf_to_docx")],
            [InlineKeyboardButton("🖼️ Extract to Images", callback_data="pdf_to_img")],
        ]
    elif ext == ".docx":
        buttons = [
            [InlineKeyboardButton("📄 Convert to PDF", callback_data="docx_to_pdf")],
        ]
    else:
        await message.reply_text("❌ Unsupported format.")
        return

    await message.reply_text(
        f"📁 File: `{file_name}`\nWhat would you like to do?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_authorized(query.from_user.id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return

    await query.answer()
    action = query.data
    file_id = context.user_data.get("file_id")
    file_name = context.user_data.get("file_name", "file")

    if not file_id:
        await query.edit_message_text("❌ Session expired.")
        return

    await query.edit_message_text("⏳ Processing...")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = os.path.join(tmpdir, file_name)

        file_obj = await context.bot.get_file(file_id)
        await file_obj.download_to_drive(input_file)

        try:
            # IMAGES
            if action in ["img_compress", "img_to_jpg", "img_to_png", "img_to_ico"]:
                exts = {"img_compress": ".jpg", "img_to_jpg": ".jpg", "img_to_png": ".png", "img_to_ico": ".ico"}
                out_path = os.path.join(tmpdir, f"out{exts[action]}")
                process_image(input_file, out_path, action)
                await context.bot.send_document(chat_id=query.message.chat_id, document=open(out_path, "rb"))

            elif action == "img_to_pdf":
                out_path = os.path.join(tmpdir, "out.pdf")
                image_to_pdf(input_file, out_path)
                await context.bot.send_document(chat_id=query.message.chat_id, document=open(out_path, "rb"))

            # DOCS
            elif action == "docx_to_pdf":
                docx_to_pdf(input_file, tmpdir)
                out_path = os.path.join(tmpdir, Path(file_name).stem + ".pdf")
                await context.bot.send_document(chat_id=query.message.chat_id, document=open(out_path, "rb"))

            elif action == "pdf_to_docx":
                out_path = os.path.join(tmpdir, Path(file_name).stem + ".docx")
                pdf_to_docx(input_file, out_path)
                await context.bot.send_document(chat_id=query.message.chat_id, document=open(out_path, "rb"))

            elif action == "pdf_to_img":
                images = pdf_to_images(input_file, tmpdir)
                for img in images:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(img, "rb"))

            # VIDEOS
            elif action in ["vid_compress", "vid_to_mp3"]:
                out_path = os.path.join(tmpdir, "out.mp4" if action == "vid_compress" else "out.mp3")
                process_video(input_file, out_path, action)
                if action == "vid_compress":
                    await context.bot.send_video(chat_id=query.message.chat_id, video=open(out_path, "rb"))
                else:
                    await context.bot.send_audio(chat_id=query.message.chat_id, audio=open(out_path, "rb"))

            await query.message.delete()

        except Exception as e:
            await query.message.reply_text(f"❌ Error: `{e}`", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("👋 Secure bot ready. Send me a file (Image, Video, PDF, DOCX).")

def main():
    if not ALLOWED_USER_ID:
        print("⚠️ ERROR: ALLOWED_USER_ID is not set!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot started and locked to your ID.")
    app.run_polling()

if __name__ == "__main__":
    main()