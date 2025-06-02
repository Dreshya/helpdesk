from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import logging
import re
import asyncio
from qa_chain import answer_query
from session_manager import init_db, log_session, send_case_email
from telegram.error import NetworkError
from settings import vector_db
from cachetools import TTLCache
from datetime import datetime, timedelta

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === State for Email Collection and Session ===
user_states = {}

# === Cache for Project to doc_id Mapping ===
project_cache = TTLCache(maxsize=100, ttl=86400)  # Cache for 24 hours

# === Closing Phrases ===
CLOSING_PHRASES = [
    "thank you", "thanks", "bye", "goodbye", "done", "ok", "okay", "cheers"
]

# === Inactivity Timeout (5 minutes) ===
INACTIVITY_TIMEOUT = timedelta(minutes=5)

# === Get Project to doc_id Mapping from Chroma ===
def get_project_doc_ids():
    """Fetch project names and doc_ids from Chroma embedding_metadata."""
    cache_key = "project_doc_ids"
    if cache_key in project_cache:
        return project_cache[cache_key]

    try:
        collection = vector_db.get()
        project_map = {}
        seen_doc_ids = set()
        for embedding_id, content, metadata in zip(collection["ids"], collection["documents"], collection["metadatas"]):
            doc_id = metadata.get("doc_id") if metadata else None
            if not doc_id:
                logger.warning(f"No doc_id found in metadata for embedding_id: {embedding_id}")
                continue
            match = re.search(r'ProjectDocumentation > ProjectInfo > ProjectName: (.*?)(?:\n|$)', content, re.IGNORECASE)
            if match:
                project_name = match.group(1).strip()
                if doc_id not in seen_doc_ids:
                    project_map[project_name.lower()] = doc_id
                    seen_doc_ids.add(doc_id)
                    logger.info(f"Found project: {project_name}, doc_id: {doc_id}, embedding_id: {embedding_id}")
            else:
                logger.warning(f"No project name found in document with embedding_id: {embedding_id}, doc_id: {doc_id}, content_snippet: {content[:100]}...")
        if not project_map:
            logger.error("No projects found in Chroma storage")
        project_cache[cache_key] = project_map
        logger.info(f"Discovered {len(project_map)} projects: {list(project_map.keys())}")
        return project_map
    except Exception as e:
        logger.error(f"Failed to fetch project doc_ids from Chroma: {e}")
        return {}

# === Check Inactivity ===
async def check_inactivity(app: Application):
    """Periodically check for inactive users and prompt with End Session button."""
    while True:
        current_time = datetime.now()
        for user_id, state in list(user_states.items()):
            if state.get("resolved_pending") and "last_message_time" in state:
                if current_time - state["last_message_time"] >= INACTIVITY_TIMEOUT:
                    try:
                        keyboard = [
                            [InlineKeyboardButton("End Session", callback_data="end_session")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await app.bot.send_message(
                            chat_id=user_id,
                            text="It looks like you're done! Click 'End Session' to provide an email for confirmation, or continue asking questions.",
                            reply_markup=reply_markup
                        )
                        logger.info(f"Prompted user {user_id} with End Session button due to inactivity")
                    except NetworkError as e:
                        logger.error(f"Failed to send inactivity prompt to user {user_id}: {e}")
        await asyncio.sleep(60)  # Check every minute

# === Telegram Handlers ===
async def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    # Reset session_ended flag to allow new session
    user_states[user_id] = {"last_message_time": datetime.now()}
    await update.message.reply_text("Hello! I'm your AI Helpdesk Bot. Please specify a project to start, e.g., 'I want to ask about the TaskTracker project.' You can then ask questions without repeating the project name.")
    logger.info(f"User {user_id} started a new session")

async def handle_message(update: Update, context: CallbackContext):
    await asyncio.sleep(0.5)
    user_id = str(update.effective_user.id)
    user_message = update.message.text.strip()
    user_message_lower = user_message.lower()
    logger.info(f"Received from {user_id}: {user_message}")

    # Check if session has ended
    if user_states.get(user_id, {}).get("session_ended", False):
        await update.message.reply_text("Your session has ended. Please use /start to begin a new session.")
        return

    # Update last message time
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]["last_message_time"] = datetime.now()

    # Check if user is providing an email
    if user_states[user_id].get("awaiting_email"):
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
                await update.message.reply_text("Thanks! I've recorded the case and sent a confirmation to your email. Please use /start to begin a new session.")
                # Fully end session by setting session_ended flag and clearing state
                user_states[user_id] = {"session_ended": True}
                logger.info(f"Session ended for user {user_id} after successful email submission")
            except Exception as e:
                logger.error(f"Failed to send email confirmation: {e}")
                await update.message.reply_text("Thanks! I've recorded the case, but there was an issue sending the email confirmation. Please use /start to begin a new session.")
                # Fully end session even if email fails
                user_states[user_id] = {"session_ended": True}
                logger.info(f"Session ended for user {user_id} after email submission (with error)")
        else:
            await update.message.reply_text("That doesn't look like a valid email. Please try again.")
        return

    # Check for project specification
    project = None
    query = user_message
    project_map = get_project_doc_ids()
    for proj_name, doc_id in project_map.items():
        if proj_name in user_message_lower:
            project = proj_name
            user_states[user_id].update({"project": project, "doc_id": doc_id})
            query = re.sub(r'\b' + re.escape(proj_name) + r'\b', '', user_message, flags=re.IGNORECASE).strip()
            logger.info(f"Selected project: {project}, doc_id: {doc_id} for user {user_id}")
            break

    # If no project specified, use stored project
    if not project:
        if user_id in user_states and "project" in user_states[user_id]:
            project = user_states[user_id]["project"]
            doc_id = user_states[user_id]["doc_id"]
            logger.info(f"Using stored project: {project}, doc_id: {doc_id} for user {user_id}")
        else:
            project_list = ", ".join(project_map.keys()) or "no projects found"
            await update.message.reply_text(f"⚠️ Please specify a project, e.g., 'I want to ask about the TaskTracker project.' Available projects: {project_list}")
            return

    # Check for closing phrases and send "End Session" button
    if any(phrase in user_message_lower for phrase in CLOSING_PHRASES):
        user_states[user_id].update({
            "resolved_pending": True,
            "query": user_states[user_id].get("query", user_message),
            "response": user_states[user_id].get("response", ""),
            "resolution": user_states[user_id].get("resolution", "pending"),
            "last_message_time": datetime.now()
        })
        # Send inline keyboard with "End Session" button
        keyboard = [
            [InlineKeyboardButton("End Session", callback_data="end_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "It looks like you're wrapping up! Click 'End Session' to provide an email for confirmation, or continue asking questions.",
            reply_markup=reply_markup
        )
        return

    # Process query
    if not query:
        await update.message.reply_text(f"Got it! You're asking about the {project} project. What specifically would you like to know?")
        return

    try:
        response, resolution = answer_query(query, user_id, doc_id)
    except Exception as e:
        logger.error(f"Error processing query for doc_id {doc_id}: {e}")
        await update.message.reply_text("OK, something broke while processing your query. Try again, please.")
        return

    log_session(user_id, user_message, response, resolution)

    for attempt in range(3):
        try:
            await update.message.reply_text(response)
            break
        except NetworkError as e:
            logger.warning(f"Network error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                await asyncio.sleep(1)
            else:
                logger.error(f"Failed to send response after 3 attempts: {e}")
                await update.message.reply_text("⚠️ I'm having trouble sending the response due to a network issue. Please try again later.")
                return

    if resolution == "resolved":
        user_states[user_id].update({
            "resolved_pending": True,
            "query": user_message,
            "response": response,
            "resolution": resolution,
            "last_message_time": datetime.now()
        })
        # Send inline keyboard with "End Session" button
        keyboard = [
            [InlineKeyboardButton("End Session", callback_data="end_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Your query seems resolved! Click 'End Session' to provide an email for confirmation, or continue asking questions.",
            reply_markup=reply_markup
        )

# === Button Callback Handler ===
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "end_session" and user_id in user_states and user_states[user_id].get("resolved_pending"):
        user_states[user_id]["awaiting_email"] = True
        user_states[user_id]["resolved_pending"] = False
        await query.message.reply_text("Please provide your email address to receive a case confirmation.")
        logger.info(f"User {user_id} clicked 'End Session' to provide email")

async def post_init(app: Application) -> None:
    """Schedule check_inactivity task after Application initialization."""
    app.create_task(check_inactivity(app))
    logger.info("Scheduled check_inactivity task")

async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("⚠️ Sorry, something went wrong. Our team is looking into it.")
        except NetworkError as e:
            logger.error(f"Network error while sending error message: {e}")
            pass

def register_handlers(app: Application):
    init_db()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    app.post_init = post_init