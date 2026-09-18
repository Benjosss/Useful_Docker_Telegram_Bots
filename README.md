# Useful Docker Telegram Bots 🤖

A collection of lightweight, highly customizable Telegram bots designed to act as your personal assistants. Built with Python and containerized with Docker (feel free to use another way to deploy them !), this repository is **ideal for hosting small, highly customizable personal bots** on a Raspberry Pi, VPS, or home server. 

Every bot is designed with privacy in mind: they are hardcoded to only respond to **your** personal Telegram User ID.

## 📦 The Bots

This repository contains three independent bots (for the moment). You can run all of them or just the ones you need.

### 1. 🖥️ `server_monitoring_bot`
Your server's dashboard right in your pocket.
* **Features:** Real-time monitoring of CPU, RAM and Disk Space.
* **Alerts:** Automatic push notifications if resources hit critical thresholds (e.g., CPU > 85%).
* **Interactive:** Send `/status` or `/top` to get current metrics and the top RAM/CPU-consuming processes via inline keyboards.

### 2. 🗜️ `files_convert_bot`
A pocket-sized Swiss Army knife for your files.
* **Features:** Send a file to the bot and interactively choose what to do with it.
* **Images:** Compress, convert formats (PNG, JPEG, ICO, WEBP).
* **Documents:** Convert DOCX to PDF (via LibreOffice), PDF to DOCX, or extract PDF pages as images.
* **Media:** Compress videos or extract audio (MP4 to MP3) using FFmpeg.

### 3. ☕ `butler_bot` (Daily Briefing)
Your morning routine automated. Every day at 6:00 AM (for example), it sends you a daily briefing.
* **Features:** Weather forecasts & outfit advice, Google Calendar events, Crypto/Stock prices, and a motivational quote.
* **Customizable:** Easily plug in other APIs (space station tracking, historical facts, etc.).

---

## ⚙️ Prerequisites

Before deploying, you need to gather a few credentials:

1. **Telegram Bot Token:**
   * Go to Telegram and search for [@BotFather](https://t.me/BotFather).
   * Send `/newbot`, choose a name, and copy the **HTTP API Token**. (You need one token per bot).
2. **Your Telegram Chat ID:**
   * Search for [@userinfobot](https://t.me/userinfobot) or similar on Telegram.
   * Start it to get your unique numeric ID. This ensures **only you** can interact with the bots.
3. **External API Keys (For `butler_bot`):**
   * Some features require third-party access. For example, to read your agenda, you will need to generate a `token.json` file using the **Google Cloud Console** (Calendar API OAuth).

---

## 🚀 Quick Deployment Tutorial

The easiest way to run these bots is using **Docker** and **Docker Compose**.

### Step 1: Clone the repository
```bash
git clone [https://github.com/Benjosss/Useful_Docker_Telegram_Bots.git](https://github.com/Benjosss/Useful_Docker_Telegram_Bots.git)
cd Useful_Docker_Telegram_Bots
```

### Step 2: Configure your environment
Navigate to the folder of the bot you want to start (e.g., `server_monitoring_bot`).
Open the `docker-compose.yml` file and replace the placeholder variables with your actual tokens:

```yaml
    environment:
      - TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
      - ALLOWED_USER_ID=987654321
```
*(For the Butler bot, make sure to place your generated Google Calendar `token.json` in the bot's root directory so it can be mounted into the container).*

### Step 3: Build and Run
Start the bot in detached mode (background):

```bash
docker compose up -d --build
```

To check the logs and make sure everything started correctly:
```bash
docker compose logs -f
```

### Step 4: Say Hello
Open Telegram, find your bot, and send `/start`. If your User ID matches the `ALLOWED_USER_ID`, the bot will reply and is ready to serve!

---

## 🛠️ Customization

These bots are templates. The true power of this setup is how easily you can hack them:
* **Add a new command:** Just create a new asynchronous function in `main.py` and register it with `CommandHandler`.
* **Add a new API:** Want the Butler to tell you the traffic on your commute? Just add a Python `requests.get()` to Google Maps API and append it to the briefing string.

Happy automating!

Benjosss :)