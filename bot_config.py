import logging
import psycopg2
import uuid
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
from telegram.error import NetworkError
from cachetools import TTLCache
from qa_chain import answer_query, clear_cache_and_memory
from session_manager import SessionManager, init_db, log_session, send_case_email, summarize_session
from settings import vector_db
from dotenv import load_dotenv
import os

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Session Manager and State ===
session_manager = SessionManager()
user_states = {}
project_cache = TTLCache(maxsize=100, ttl=86400)
CLOSING_PHRASES = ["thank you", "thanks", "bye", "goodbye", "done", "ok", "okay", "cheers"]
INACTIVITY_TIMEOUT = timedelta(minutes=5)

# === Database Connection ===
def get_db_connection():
    load_dotenv()
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    conn.cursor_factory = psycopg2.extras.DictCursor
    return conn

# === Check Subscription and Project Access ===
def check_access(chat_id: str, doc_id: str = None) -> tuple:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.business_id, e.employee_id, b.name
            FROM Employees e
            JOIN Businesses b ON e.business_id = b.business_id
            WHERE e.chat_id = %s
            """,
            (chat_id,)
        )
        employee = cursor.fetchone()
        if not employee:
            return False, "You are not registered. Use /register <code> to link your account."

        business_id = employee['business_id']
        employee_id = employee['employee_id']
        cursor.execute(
            """
            SELECT subscription_id
            FROM Subscriptions
            WHERE business_id = %s AND end_date >= CURRENT_DATE AND start_date <= CURRENT_DATE
            """,
            (business_id,)
        )
        subscription = cursor.fetchone()
        if not subscription:
            # Clear chat_id if subscription expired
            cursor.execute(
                "UPDATE Employees SET chat_id = NULL WHERE employee_id = %s",
                (employee_id,)
            )
            conn.commit()
            return False, "Your company's subscription has expired. Your chat ID has been cleared. Please contact your admin."

        if doc_id:
            cursor.execute(
                "SELECT access_id FROM ProjectAccess WHERE business_id = %s AND doc_id = %s",
                (business_id, doc_id)
            )
            if not cursor.fetchone():
                return False, f"You do not have access to project {doc_id}."
        
        return True, None
    finally:
        cursor.close()
        conn.close()

# === Get Project to doc_id Mapping from Chroma ===
def get_project_doc_ids(chat_id: str):
    cache_key = f"project_doc_ids_{chat_id}"
    if cache_key in project_cache:
        return project_cache[cache_key]

    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT business_id FROM Employees WHERE chat_id = %s", (chat_id,))
            employee = cursor.fetchone()
            if not employee:
                logger.error(f"No employee found for chat_id: {chat_id}")
                return {}
            business_id = employee['business_id']
        finally:
            cursor.close()
            conn.close()

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT doc_id, doc_name FROM ProjectAccess WHERE business_id = %s",
                (business_id,)
            )
            project_access = cursor.fetchall()
            accessible_doc_ids = {row['doc_id']: row['doc_name'] for row in project_access}
        finally:
            cursor.close()
            conn.close()

        collection = vector_db.get()
        project_map = {}
        seen_doc_ids = set()
        for embedding_id, content, metadata in zip(collection["ids"], collection["documents"], collection["metadatas"]):
            doc_id = metadata.get("doc_id") if metadata else None
            if not doc_id or doc_id not in accessible_doc_ids:
                continue
            match = re.search(r'ProjectDocumentation > ProjectInfo > ProjectName: (.*?)(?:\n|$)', content, re.IGNORECASE)
            project_name = match.group(1).strip() if match else accessible_doc_ids[doc_id] or doc_id
            if doc_id not in seen_doc_ids:
                project_map[project_name.lower()] = doc_id
                seen_doc_ids.add(doc_id)
                logger.info(f"Found project: {project_name}, doc_id: {doc_id}, embedding_id: {embedding_id} for business_id: {business_id}")
        if not project_map:
            logger.error(f"No accessible projects found for business_id: {business_id}")
        project_cache[cache_key] = project_map
        logger.info(f"Discovered {len(project_map)} projects for chat_id {chat_id}: {list(project_map.keys())}")
        return project_map
    except Exception as e:
        logger.error(f"Failed to fetch project doc_ids for chat_id {chat_id}: {e}")
        return {}

# === Check Inactivity ===
async def check_inactivity(app: Application):
    while True:
        current_time = datetime.now()
        for user_id, state in list(user_states.items()):
            if state.get("resolved_pending") and "last_message_time" in state:
                if current_time - state["last_message_time"] >= INACTIVITY_TIMEOUT:
                    try:
                        keyboard = [
                            [InlineKeyboardButton("Resolved", callback_data="resolve_session"),
                             InlineKeyboardButton("Unresolved", callback_data="unresolve_session")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await app.bot.send_message(
                            chat_id=user_id,
                            text="It looks like you're done! Was your query resolved or unresolved? Please select an option.",
                            reply_markup=reply_markup
                        )
                        logger.info(f"Prompted user {user_id} with resolution buttons due to inactivity")
                    except NetworkError as e:
                        logger.error(f"Failed to send inactivity prompt to user {user_id}: {e}")
        await asyncio.sleep(60)

# === Telegram Handlers ===
async def register(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Please provide a registration code: /register <code>")
        return
    
    code = context.args[0]
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT employee_id, business_id, email FROM Employees WHERE registration_code = %s AND chat_id IS NULL",
            (code,)
        )
        employee = cursor.fetchone()
        if not employee:
            await update.message.reply_text("Invalid or used registration code.")
            return
        
        cursor.execute(
            "UPDATE Employees SET chat_id = %s, registration_code = NULL WHERE employee_id = %s",
            (user_id, employee['employee_id'])
        )
        conn.commit()
        await update.message.reply_text(f"Registered successfully for {employee['email']}!")
    finally:
        cursor.close()
        conn.close()

async def handle_message(update: Update, context: CallbackContext):
    await asyncio.sleep(0.5)
    user_id = str(update.effective_user.id)
    user_message = update.message.text.strip()
    user_message_lower = user_message.lower()
    logger.info(f"Received from {user_id}: {user_message}")

    if user_id not in user_states or user_states[user_id].get("session_ended", False):
        user_states[user_id] = {"last_message_time": datetime.now(), "session_ended": False}
        project_map = get_project_doc_ids(user_id)
        project_list = ", ".join(project_map.keys()) or "no projects available"
        await update.message.reply_text(
            f"Hi! I'm your AI Helpdesk Bot. Register with /register <code> or ask about a project with #doc_id (e.g., 'Tell me about IMS #ims_v1') or specify a project name (e.g., 'I want to ask about the TaskTracker project'). Available projects: {project_list}"
        )
        logger.info(f"Started new session for user {user_id}")
        return

    user_states[user_id]["last_message_time"] = datetime.now()

    if user_states[user_id].get("awaiting_email"):
        email = user_message.strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            session_id = user_states[user_id].get("session_id")
            is_unresolved = user_states[user_id].get("is_unresolved", False)
            summary = user_states[user_id].get("summary", "No summary available.")
            log_text = user_states[user_id].get("log_text", "No log available.")
            log_session(
                user_id,
                user_states[user_id].get("query", ""),
                user_states[user_id].get("response", ""),
                "unresolved" if is_unresolved else "resolved",
                email=email,
                session_id=session_id,
                summary=summary if is_unresolved else None
            )
            try:
                send_case_email(email, session_id, is_unresolved, summary, log_text)
                await update.message.reply_text("Thanks! I've recorded the case and sent a confirmation to your email. Start a new session by sending any message.")
                user_states[user_id] = {}
                logger.info(f"Session ended for user {user_id} after successful email submission")
            except Exception as e:
                logger.error(f"Failed to send email confirmation: {e}")
                await update.message.reply_text("Thanks! I've recorded the case, but there was an issue sending the email confirmation. Start a new session by sending any message.")
                user_states[user_id] = {}
                logger.info(f"Session ended for user {user_id} after email submission (with error)")
        else:
            await update.message.reply_text("That doesn't look like a valid email. Please try again.")
        return

    doc_id = None
    query = user_message
    if "#" in user_message:
        parts = user_message.split("#")
        query = parts[0].strip()
        doc_id = parts[1].strip()

    has_access, error_message = check_access(user_id, doc_id)
    if not has_access:
        await update.message.reply_text(error_message)
        return

    project = None
    project_map = get_project_doc_ids(user_id)
    for proj_name, proj_doc_id in project_map.items():
        if proj_name in user_message_lower:
            project = proj_name
            doc_id = proj_doc_id
            user_states[user_id].update({"project": project, "doc_id": doc_id})
            query = re.sub(r'\b' + re.escape(proj_name) + r'\b', '', user_message, flags=re.IGNORECASE).strip()
            logger.info(f"Selected project: {project}, doc_id: {doc_id} for user {user_id}")
            break

    if not project and not doc_id:
        if user_id in user_states and "project" in user_states[user_id]:
            project = user_states[user_id]["project"]
            doc_id = user_states[user_id]["doc_id"]
            logger.info(f"Using stored project: {project}, doc_id: {doc_id} for user {user_id}")
        else:
            project_list = ", ".join(project_map.keys()) or "no projects available"
            await update.message.reply_text(f"⚠️ Please specify a project, e.g., 'I want to ask about the TaskTracker project.' Available projects: {project_list}")
            return

    if any(phrase in user_message_lower for phrase in CLOSING_PHRASES):
        user_states[user_id].update({
            "resolved_pending": True,
            "query": user_states[user_id].get("query", user_message),
            "response": user_states[user_id].get("response", ""),
            "resolution": "pending",
            "last_message_time": datetime.now(),
            "session_id": user_states[user_id].get("session_id", str(uuid.uuid4()))
        })
        keyboard = [
            [InlineKeyboardButton("Resolved", callback_data="resolve_session"),
             InlineKeyboardButton("Unresolved", callback_data="unresolve_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "It looks like you're wrapping up! Was your query resolved or unresolved? Please select an option.",
            reply_markup=reply_markup
        )
        return

    if not query:
        await update.message.reply_text(f"Got it! You're asking about the {project} project. What specifically would you like to know?")
        return

    session_id = session_manager.get_session(user_id) or str(uuid.uuid4())
    session_manager.set_session(user_id, session_id)

    try:
        response = answer_query(query, user_id, doc_id)
        if not response or "couldn't find relevant information" in response.lower():
            response = f"I couldn't find specific details for '{query}' in the {project} documentation. Could you clarify or ask about another aspect?"
        
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

        log_session(user_id, user_message, response, "pending", session_id=session_id)
        user_states[user_id].update({
            "query": user_message,
            "response": response,
            "resolution": "pending",
            "last_message_time": datetime.now(),
            "session_id": session_id
        })

    except Exception as e:
        logger.error(f"Error processing query for user {user_id}, doc_id: {doc_id}: {e}")
        error_response = "Sorry, something went wrong while processing your query. Please try again."
        for attempt in range(3):
            try:
                await update.message.reply_text(error_response)
                break
            except NetworkError as e:
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Failed to send error response after 3 attempts: {e}")
                    return

# === Button Callback Handler ===
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data in ["resolve_session", "unresolve_session"] and user_id in user_states and user_states[user_id].get("resolved_pending"):
        is_unresolved = query.data == "unresolve_session"
        session_id = user_states[user_id].get("session_id", str(uuid.uuid4()))

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT query, response FROM QueryLogs WHERE session_id = %s ORDER BY timestamp",
                (session_id,)
            )
            logs = cursor.fetchall()
            log_text = "\n".join([f"Q: {log['query']}\nA: {log['response']}" for log in logs])
        finally:
            cursor.close()
            conn.close()

        summary = summarize_session(log_text)

        from qa_chain import end_session
        end_session(user_id)
        user_states[user_id] = {
            "awaiting_email": True,
            "is_unresolved": is_unresolved,
            "summary": summary,
            "log_text": log_text,
            "session_id": session_id
        }
        await query.message.reply_text("Please provide your email address to receive a case confirmation.")
        logger.info(f"User {user_id} marked session as {'unresolved' if is_unresolved else 'resolved'} and prompted for email")

# === Error Handler ===
async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("⚠️ Sorry, something went wrong. Our team is looking into it.")
        except NetworkError as e:
            logger.error(f"Network error while sending error message: {e}")

# === Bot Setup ===
def setup_bot(token: str):
    application = Application.builder().token(token).build()
    init_db()
    application.add_handler(CommandHandler("register", register))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    return application