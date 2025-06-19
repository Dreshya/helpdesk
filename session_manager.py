import psycopg2
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from langchain.prompts import PromptTemplate
from settings import llm
from psycopg2.extras import DictCursor

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
        self.sessions = {}

    def get_session(self, user_id: str) -> str:
        return self.sessions.get(user_id)

    def set_session(self, user_id: str, session_id: str):
        self.sessions[user_id] = session_id
        logger.info(f"Set session for user {user_id}: {session_id}")

    def clear_session(self, user_id: str):
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")

def init_db():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Businesses (
            business_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Employees (
            employee_id SERIAL PRIMARY KEY,
            business_id INTEGER REFERENCES Businesses(business_id) ON DELETE CASCADE,
            employee_name TEXT NOT NULL,
            email TEXT NOT NULL,
            chat_id TEXT,
            registration_code TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Subscriptions (
            subscription_id SERIAL PRIMARY KEY,
            business_id INTEGER REFERENCES Businesses(business_id) ON DELETE CASCADE,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ProjectAccess (
            access_id SERIAL PRIMARY KEY,
            business_id INTEGER REFERENCES Businesses(business_id) ON DELETE CASCADE,
            doc_id TEXT NOT NULL,
            doc_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS QueryLogs (
            id SERIAL PRIMARY KEY,
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
    cursor.close()
    conn.close()
    logger.info("Initialized helpdesk database with updated schema")

def log_session(user_id: str, query: str, response: str, resolution: str, email: str = None, session_id: str = None, summary: str = None):
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    cursor = conn.cursor()
    # Generate timestamp as ISO string
    timestamp = datetime.utcnow().isoformat()
    try:
        cursor.execute(
            """
            INSERT INTO QueryLogs (chat_id, query, response, resolution_status, session_id, timestamp, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, query, response, resolution, session_id, timestamp, summary if resolution == "unresolved" else None)
        )
        conn.commit()
        logger.info(f"Logged session for user {user_id}, session_id: {session_id}, query: {query[:50]}..., summary: {summary[:50] if summary else 'None'}...")
    except Exception as e:
        logger.error(f"Failed to log session for user {user_id}: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

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
        prompt = summary_prompt_template.format(log_text=log_text)
        summary = llm.invoke(prompt).strip()
        words = summary.split()
        if len(words) > 100:
            summary = " ".join(words[:100]) + "..."
        return summary if summary else "Brief interaction with no significant details"
    except Exception as e:
        logger.error(f"Failed to summarize session: {e}")
        return "Brief interaction with no significant details"