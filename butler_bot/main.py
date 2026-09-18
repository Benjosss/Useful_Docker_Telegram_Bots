import os
import datetime
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- SECURITY CONFIG ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# --- PLACE CONFIG ---
LAT = "49.13"
LON = "6.16"

# --- DATA COLECTION ---

def get_space_people():
    """Show number of astronauts in space"""
    try:
        r = requests.get("http://api.open-notify.org/astros.json", timeout=30).json()
        nb = r.get("number", 0)
        return f"🚀 *Space* : They are now {nb} humans in space."
    except Exception as e:
        return f"🚀 *Space* : (Erreur : {e})"

def get_weather():
    """Get meteo via Open-Meteo"""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FParis"
    try:
        r = requests.get(url, timeout=5).json()
        temp_max = r["daily"]["temperature_2m_max"][0]
        temp_min = r["daily"]["temperature_2m_min"][0]
        rain_prob = r["daily"]["precipitation_probability_max"][0]

        conseil = ""
        if rain_prob > 50:
            conseil += "☔ Take an umbrella !\n"
        if temp_max < 10:
            conseil += "🧥 It's cold outside !\n"
        elif temp_max > 25:
            conseil += "🕶️ A hot day ahead !\n"

        return f"🌡️ *Meteo* : {temp_min}°C to {temp_max}°C (Rain : {rain_prob}%)\n{conseil}"
    except Exception as e:
        return f"🌡️ *Meteo* : ({e})"

def get_btc_price():
    """Get Bitcoin price via CoinGecko."""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur", timeout=5).json()
        price = r["bitcoin"]["eur"]
        return f"💰 *Bitcoin* : {price:,.2f} €"
    except Exception:
        return "💰 *Bitcoin* : Unavailable"

def get_quote():
    """ Retrieve a motivational quote. """
    try:
        r = requests.get("https://zenquotes.io/api/today", timeout=5).json()
        quote = r[0]['q']
        author = r[0]['a']
        return f"💡 *Daily quote* :\n_« {quote} »_ - {author}"
    except Exception:
        return "💡 *Daily quote* : Be the best version of yourself."

def get_calendar_events():
    """Get Google Calendar events of the day."""
    # token.json file have user access.
    if not os.path.exists('token.json'):
        return "📅 *Calendar* : Not configured. (token.json file missing)"

    try:
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar.readonly'])
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        end_of_day = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=end_of_day,
            maxResults=5, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return "📅 *Calendar* : No events for today. 🎉"

        agenda = "📅 *Today program* :\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            time_str = "All day " if 'T' not in start else datetime.datetime.fromisoformat(start).strftime('%H:%M')
            agenda += f"🔹 {time_str} - {event['summary']}\n"
        return agenda
    except Exception as e:
        return f"📅 *Calendar* : Sync error ({e})"

# --- GENERATION AND SEND ---

def build_briefing():
    """Compile all infos in a single message"""
    date_str = datetime.datetime.now().strftime("%d/%m/%Y")

    parts = [
        f"☕ *Hi ! Here's your {date_str} briefing*",
        get_weather(),
        get_calendar_events(),
        get_btc_price(),
        get_quote(),
        get_space_people()
    ]
    return "\n\n".join(parts)

async def send_daily_briefing(context: ContextTypes.DEFAULT_TYPE):
    """Function called by the scheduler every morning."""
    briefing = build_briefing()
    await context.bot.send_message(chat_id=ALLOWED_USER_ID, text=briefing, parse_mode="Markdown")

async def manual_briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger the briefing manually via /briefing."""
    if update.effective_user.id != ALLOWED_USER_ID:
        print(f"⛔ Blocage de {update.effective_user.id}")
        return

    await update.message.reply_text("🔄 *Generating briefing...*", parse_mode="Markdown")
    briefing = build_briefing()
    await update.message.reply_text(briefing, parse_mode="Markdown")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await update.message.reply_text("👋 Butler ready. Type /briefing to test, or wait until tomorrow morning at 6:00 AM.")

def main():
    if not ALLOWED_USER_ID:
        raise ValueError("TELEGRAM_CHAT_ID manquant.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Adding manual controls
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("briefing", manual_briefing_command))

    # Scheduling the daily message (e.g., 06:00 AM, server time)    
    target_time = datetime.time(hour=6, minute=0, second=0)
    app.job_queue.run_daily(send_daily_briefing, time=target_time)

    print("🤖 Morning Butler started...")
    app.run_polling()

if __name__ == "__main__":
    main()