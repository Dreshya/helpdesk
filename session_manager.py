import sqlite3
from datetime import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TEXT,
            query TEXT,
            response TEXT,
            resolution TEXT,
            email TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_session(user_id: str, query: str, response: str, resolution: str, email: str = None):
    conn = sqlite3.connect("sessions.db")
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO sessions (user_id, timestamp, query, response, resolution, email) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, timestamp, query, response, resolution, email)
    )
    conn.commit()
    conn.close()

def send_case_email(email: str, query: str, response: str):
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
    msg["Subject"] = "AI Helpdesk Case Confirmation"

    body = f"""
    Dear User,

    Your query has been resolved. Below are the details:

    Query: {query}
    Response: {response}

    Thank you for using our AI Helpdesk!
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, email, msg.as_string())
        logger.info(f"Email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")