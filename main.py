from telegram.ext import Application
from bot_config import register_handlers
from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
    app = Application.builder().token(token).build()
    register_handlers(app)
    print("✅ AI Helpdesk Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()