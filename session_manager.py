import sqlite3
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from langchain.prompts import PromptTemplate
from settings import llm

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Summarization Prompt Template ===
summary_prompt_template = PromptTemplate.from_template("""
You are a support bot tasked with summarizing a conversation log **in English only**. **Do not use external knowledge, assumptions, or general information.** Provide a concise summary (up to 100 words) based solely on the provided conversation log. If the log is empty or lacks meaningful content, return: "Brief interaction with no significant details."

Conversation Log:
{log_text}

Summary (in English):
""")

# === SessionManager Class ===
class SessionManager:
    def __init__(self):
        self.sessions = {}  # In-memory storage for user_id -> session_id mapping

    def get_session(self, user_id: str) -> str:
        """Retrieve the session ID for a given user_id."""
        return self.sessions.get(user_id)

    def set_session(self, user_id: str, session_id: str):
        """Set the session ID for a given user_id."""
        self.sessions[user_id] = session_id
        logger.info(f"Set session for user {user_id}: {session_id}")

    def clear_session(self, user_id: str):
        """Clear the session for a given user_id."""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")

def init_db():
    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    # Create QueryLogs table with summary column for unresolved queries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS QueryLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            resolution_status TEXT NOT NULL,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            summary TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Initialized helpdesk.db with updated schema")

def log_session(user_id: str, query: str, response: str, resolution: str, email: str = None, session_id: str = None, summary: str = None):
    conn = sqlite3.connect("helpdesk.db")
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO QueryLogs (chat_id, query, response, resolution_status, session_id, timestamp, summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, query, response, resolution, session_id, timestamp, summary if resolution == "unresolved" else None)
    )
    conn.commit()
    conn.close()
    logger.info(f"Logged session for user {user_id}, session_id: {session_id}, query: {query[:50]}..., summary: {summary[:50] if summary else 'None'}...")

def send_case_email(email: str, session_id: str, is_unresolved: bool, summary: str, log_text: str):
    load_dotenv()
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([sender_email, smtp_password]):
        logger.error("SMTP credentials not configured")
        return

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    # Set subject based on resolution status
    msg["Subject"] = f"{'UNRESOLVED' if is_unresolved else 'RESOLVED'}: AI Helpdesk Session Log (Session ID: {session_id})"
    if is_unresolved:
        msg["Cc"] = "support@company.com"

    body = f"""
Dear User,

Below is the summary and full log of your recent session with the AI Helpdesk:

Session Summary:
{summary}

Full Conversation Log:
{log_text}

Thank you for using our AI Helpdesk!
"""
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, [email] + (["support@company.com"] if is_unresolved else []), msg.as_string())
        logger.info(f"Email sent to {email}, CC: {'support@company.com' if is_unresolved else 'None'}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")

def summarize_session(log_text: str) -> str:
    if not log_text.strip():
        return "Brief interaction with no significant details"
    
    try:
        # Use LLM to generate a summary
        prompt = summary_prompt_template.format(log_text=log_text)
        summary = llm.invoke(prompt).strip()
        # Ensure summary is within 100 words
        words = summary.split()
        if len(words) > 100:
            summary = " ".join(words[:100]) + "..."
        return summary if summary else "Brief interaction with no significant details"
    except Exception as e:
        logger.error(f"Failed to summarize session: {e}")
        return "Brief interaction with no significant details"