from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
from qa_chain import answer_query

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Telegram Handlers ===
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. How can I assist you?")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"Received from {user_id}: {user_message}")

    response = answer_query(user_message)
    await update.message.reply_text(response)

async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Optional: Notify the user
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Sorry, something went wrong. Our team is looking into it.")

def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)




