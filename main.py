import asyncio
from telegram.ext import Application
from bot_config import setup_bot
from qa_chain import clear_cache_and_memory
from bot_config import check_inactivity  # Import check_inactivity
from dotenv import load_dotenv
import os

async def start_background_tasks(app):
    # Schedule the check_inactivity task
    app.create_task(check_inactivity(app))

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found")
    
    clear_cache_and_memory()  # Clear cache on startup
    app = setup_bot(token)  # Create application
    print("✅ AI Helpdesk Bot is running...")
    
    # Run the application and background tasks
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_background_tasks(app))
    app.run_polling()

if __name__ == "__main__":
    main()