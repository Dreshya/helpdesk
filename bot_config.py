from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import asyncio
from telegram.error import NetworkError
from qa_chain import answer_query

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Telegram Handlers ===
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. How can I assist you?")

async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    logger.info(f"Received: {user_message}")

    response = answer_query(user_message)
    await update.message.reply_text(response)

async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Optional: Notify the user
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Sorry, something went wrong. Our team is looking into it.")

async def safe_reply(update, context, response):
    try:
        await update.message.reply_text(response)
    except NetworkError as e:
        print(f"NetworkError occurred: {e}")
        # Optional: wait and retry
        await asyncio.sleep(2)
        try:
            await update.message.reply_text("Sorry for the delay. Here's your reply:\n" + response)
        except Exception as ex:
            print(f"Second attempt failed: {ex}")

def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    await app.safe_reply(update, context, response)





