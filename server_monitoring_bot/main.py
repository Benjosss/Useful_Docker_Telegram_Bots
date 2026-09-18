import os
import asyncio
import psutil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# From env variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# User check to allow only your ID to speak to your bot on Telegram app
ALLOWED_USER_ID = int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else 0

CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "85.0")) # Default value : 85% CPU usage
RAM_THRESHOLD = float(os.getenv("RAM_THRESHOLD", "90.0")) # Default value : 90% RAM usage
DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "90.0")) # Default value : 90% Disk usage
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60")) # Default value : 60 seconds

# --- UTILS ---

def get_system_stats():
    """Gather resources status"""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    text = (
        "🖥️ *Server Status Report*\n\n"
        f"⚙️ *CPU* : `{cpu}%`\n"
        f"🧠 *RAM* : `{ram.percent}%` ({ram.used / (1024**3):.2f} / {ram.total / (1024**3):.2f} Go)\n"
        f"💾 *Disk* : `{disk.percent}%` ({disk.free / (1024**3):.2f} Go disponibles)"
    )
    return text

def get_top_processes():
    """List 5 processes that uses more RAM."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Memory usage sort
    top_proc = sorted(processes, key=lambda p: p['memory_percent'] or 0, reverse=True)[:5]

    text = "🔥 *Top 5 processes (RAM)* :\n\n"
    for p in top_proc:
        text += f"• `{p['name']}` (PID {p['pid']}) : `{p['memory_percent']:.1f}%`\n"
    return text

def build_keyboard():
    """Create inline keyboard buttons"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
            InlineKeyboardButton("🔥 Top processes", callback_data="top_proc")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- COMMANDS AND TELEGRAM INTERACTIONS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start or /help"""
    # SECURITY : Lock other users than you
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    await update.message.reply_text(
        "👋 *Monitoring bot connected !*\n\n"
        "Available commands  :\n"
        "/status - Show actual metrics\n"
        "/top - Show most resource-intensive processes",
        parse_mode="Markdown",
        reply_markup=build_keyboard()
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /status"""
    # SECURITY : Lock other users than you
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    await update.message.reply_text(
        get_system_stats(),
        parse_mode="Markdown",
        reply_markup=build_keyboard()
    )

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /top"""
    # SECURITY : Lock other users than you
    if update.effective_user.id != ALLOWED_USER_ID:
        return

    await update.message.reply_text(
        get_top_processes(),
        parse_mode="Markdown",
        reply_markup=build_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clicks handler (Inline Keyboard)"""
    query = update.callback_query

    # SECURITY : Lock other users than you
    if query.from_user.id != ALLOWED_USER_ID:
        await query.answer("⛔ You're not allowed to use this bot", show_alert=True)
        return

    await query.answer()

    if query.data == "refresh":
        new_text = get_system_stats()
        # Refresh message only if data changed
        if query.message.text != new_text:
            await query.edit_message_text(
                new_text,
                parse_mode="Markdown",
                reply_markup=build_keyboard()
            )
    elif query.data == "top_proc":
        await query.message.reply_text(
            get_top_processes(),
            parse_mode="Markdown",
            reply_markup=build_keyboard()
        )

# --- BACKGROUND TASK (AUTOMATIC MONITORING) ---

async def monitor_loop(app: Application):
    """Periodic background check."""
    while True:
        try:
            alerts = []
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            if cpu > CPU_THRESHOLD:
                alerts.append(f"⚠️ *CPU saturated* : `{cpu}%` (Threshold : {CPU_THRESHOLD}%)")
            if ram.percent > RAM_THRESHOLD:
                alerts.append(f"⚠️ *RAM saturated* : `{ram.percent}%` (Threshold : {RAM_THRESHOLD}%)")
            if disk.percent > DISK_THRESHOLD:
                alerts.append(f"⚠️ *Disk saturated* : `{disk.percent}%` (Threshold : {DISK_THRESHOLD}%)")

            if alerts and TELEGRAM_CHAT_ID:
                msg = "🚨 *Resources alert detected*\n\n" + "\n".join(alerts)
                await app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=msg,
                    parse_mode="Markdown",
                    reply_markup=build_keyboard()
                )

        except Exception as e:
            print(f"Error in monitoring loop : {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# --- INIT ---

async def post_init(app: Application):
    """Lauch background task after bot init"""
    asyncio.create_task(monitor_loop(app))

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not specified.")
    if not ALLOWED_USER_ID:
        print("⚠️ WARNING : TELEGRAM_CHAT_ID not specified")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Commands save
    app.add_handler(CommandHandler(["start", "help"], start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("top", top_command))

    # Button manager registration
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Monitoring bot started and secured...")
    app.run_polling()

if __name__ == "__main__":
    main()