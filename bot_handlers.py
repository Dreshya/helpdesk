from telegram import Update
from telegram.ext import CallbackContext
from qa_engine import generate_response
from database import save_query

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. How can I assist you?")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_message = update.message.text

    response_text = generate_response(user_message)

    save_query(user_id, user_message, response_text, thread_id="thread_001")
    await update.message.reply_text(response_text)