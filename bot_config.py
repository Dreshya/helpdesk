from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import re
import asyncio
from qa_chain import answer_query
from session_manager import init_db, log_session, send_case_email
from telegram.error import NetworkError

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === State for Email Collection and Session ===
user_states = {}

# === Telegram Handlers ===
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. Please include a document ID in your first query, e.g., '#alpha_2025 How do I reset?' Subsequent queries will use the same document ID unless changed.")

async def handle_message(update: Update, context: CallbackContext):
    await asyncio.sleep(0.5)  # Add 0.5s delay to avoid rate limits
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    logger.info(f"Received from {user_id}: {user_message}")

    # Check if user is providing an email
    if user_id in user_states and user_states[user_id].get("awaiting_email"):
        email = user_message.strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            log_session(
                user_id,
                user_states[user_id]["query"],
                user_states[user_id]["response"],
                user_states[user_id]["resolution"],
                email
            )
            try:
                send_case_email(email, user_states[user_id]["query"], user_states[user_id]["response"])
                await update.message.reply_text("Thanks! I've recorded the case and sent a confirmation to your email.")
            except Exception as e:
                logger.error(f"Failed to send email confirmation: {e}")
                await update.message.reply_text("Thanks! I've recorded the case, but there was an issue sending the email confirmation.")
            # Preserve doc_id after email submission
            doc_id = user_states[user_id].get("doc_id")
            user_states[user_id] = {"doc_id": doc_id} if doc_id else {}
        else:
            await update.message.reply_text("That doesn't look like a valid email. Please try again.")
        return

    # Clear any stale state for new queries
    if user_id in user_states and not user_states[user_id].get("awaiting_email"):
        logger.warning(f"Clearing stale state for user {user_id}")
        del user_states[user_id]

    # Process query
    match = re.match(r"#(\w+)\s+(.+)", user_message)
    if match:
        doc_id, query = match.groups()
        user_states[user_id] = user_states.get(user_id, {})
        user_states[user_id]["doc_id"] = doc_id
    else:
        if user_id not in user_states or "doc_id" not in user_states[user_id]:
            await update.message.reply_text("⚠️ Please include a document ID in your query, e.g., '#alpha_2025 How do I reset?'")
            return
        doc_id = user_states[user_id]["doc_id"]
        query = user_message

    try:
        response, resolution = answer_query(query, user_id, doc_id)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        await update.message.reply_text("Sorry, something went wrong while processing your query. Please try again.")
        return

    log_session(user_id, user_message, response, resolution)
    
    # Retry sending response up to 3 times
    for attempt in range(3):
        try:
            await update.message.reply_text(response)
            break
        except NetworkError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                await asyncio.sleep(1)  # Wait 1 second before retrying
            else:
                logger.error(f"Failed to send response after 3 attempts: {e}")
                await update.message.reply_text("⚠️ I'm having trouble sending the response due to a network issue. Please try again later.")
                return
    
    if resolution == "resolved":
        user_states[user_id] = {
            "awaiting_email": True,
            "query": user_message,
            "response": response,
            "resolution": resolution,
            "doc_id": doc_id  # Preserve doc_id for next query
        }
        await update.message.reply_text("Looks like your query was resolved! Please share your email address so I can send you a case confirmation.")

async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("⚠️ Sorry, something went wrong. Our team is looking into it.")
        except NetworkError as e:
            logger.error(f"Network error while sending error message: {e}")
            # Suppress the network error to prevent bot crash
            pass

def register_handlers(app: Application):
    init_db()  # Initialize database
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)