import streamlit as st
import psycopg2
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
import logging
from psycopg2.extras import DictCursor

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    conn.cursor_factory = DictCursor
    return conn

# === Send Registration Email ===
def send_registration_email(email: str, registration_code: str, entity_type: str, entity_name: str):
    load_dotenv()
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([sender_email, smtp_password]):
        logger.error("SMTP credentials not configured")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = f"AI Helpdesk Registration Code for {entity_name}"

    body = f"""
Dear {entity_type} ({entity_name}),

Your registration code for the AI Helpdesk is: {registration_code}

Please use this code in Telegram with the command: /register {registration_code}

This code is required to access the helpdesk for the first time. Keep it secure.

Thank you,
AI Helpdesk Team
"""
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, [email], msg.as_string())
        logger.info(f"Registration email sent to {email} with code {registration_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send registration email to {email}: {e}")
        return False

# === Streamlit Dashboard ===
st.title("AI Helpdesk Admin Dashboard")
st.write("Manage businesses, employees, subscriptions, and project documentation.")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["Businesses", "Employees", "Subscriptions", "Projects"])

# --- Businesses Tab ---
with tab1:
    st.header("Manage Businesses")
    
    # Add New Business
    st.subheader("Add New Business")
    with st.form("add_business_form"):
        business_name = st.text_input("Business Name")
        business_email = st.text_input("Business Email")
        submitted = st.form_submit_button("Add Business")
        if submitted:
            if not business_name or not business_email:
                st.error("Business name and email are required.")
            else:
                registration_code = str(uuid.uuid4())
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO Businesses (name, email) VALUES (%s, %s) RETURNING business_id",
                        (business_name, business_email)
                    )
                    business_id = cursor.fetchone()['business_id']
                    conn.commit()
                    if send_registration_email(business_email, registration_code, "Business", business_name):
                        st.success(f"Business '{business_name}' added and registration code sent to {business_email}.")
                    else:
                        st.error("Business added but failed to send registration email.")
                except Exception as e:
                    st.error(f"Failed to add business: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()

    # List Existing Businesses
    st.subheader("Existing Businesses")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT business_id, name, email FROM Businesses ORDER BY name")
        businesses = cursor.fetchall()
        if businesses:
            for biz in businesses:
                st.write(f"ID: {biz['business_id']} | Name: {biz['name']} | Email: {biz['email']}")
        else:
            st.info("No businesses found.")
    finally:
        cursor.close()
        conn.close()

# --- Employees Tab ---
with tab2:
    st.header("Manage Employees")
    
    # Add New Employee
    st.subheader("Add New Employee")
    with st.form("add_employee_form"):
        employee_name = st.text_input("Employee Name")
        employee_email = st.text_input("Employee Email")
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT business_id, name FROM Businesses ORDER BY name")
            businesses = cursor.fetchall()
            business_options = {biz['name']: biz['business_id'] for biz in businesses}
            business_name = st.selectbox("Business Name", options=list(business_options.keys()))
        finally:
            cursor.close()
            conn.close()
        submitted = st.form_submit_button("Add Employee")
        if submitted:
            if not employee_name or not employee_email or not business_name:
                st.error("Employee name, email, and business name are required.")
            else:
                registration_code = str(uuid.uuid4())
                business_id = business_options[business_name]
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO Employees (business_id, employee_name, email, registration_code) VALUES (%s, %s, %s, %s)",
                        (business_id, employee_name, employee_email, registration_code)
                    )
                    conn.commit()
                    if send_registration_email(employee_email, registration_code, "Employee", employee_name):
                        st.success(f"Employee '{employee_name}' added and registration code sent to {employee_email}.")
                    else:
                        st.error("Employee added but failed to send registration email.")
                except Exception as e:
                    st.error(f"Failed to add employee: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()

    # List Existing Employees
    st.subheader("Existing Employees")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.employee_id, e.employee_name, e.email, e.chat_id, b.name AS business_name
            FROM Employees e JOIN Businesses b ON e.business_id = b.business_id
            ORDER BY e.employee_name
        """)
        employees = cursor.fetchall()
        if employees:
            for emp in employees:
                st.write(f"ID: {emp['employee_id']} | Name: {emp['employee_name']} | Email: {emp['email']} | Business: {emp['business_name']} | Chat ID: {emp['chat_id'] or 'Not registered'}")
        else:
            st.info("No employees found.")
    finally:
        cursor.close()
        conn.close()

# --- Subscriptions Tab ---
with tab3:
    st.header("Manage Subscriptions")
    
    # Add New Subscription
    st.subheader("Add New Subscription")
    with st.form("add_subscription_form"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT business_id, name FROM Businesses ORDER BY name")
            businesses = cursor.fetchall()
            business_options = {biz['name']: biz['business_id'] for biz in businesses}
            business_name = st.selectbox("Business Name", options=list(business_options.keys()), key="sub_business")
        finally:
            cursor.close()
            conn.close()
        start_date = st.date_input("Subscription Start Date")
        end_date = st.date_input("Subscription End Date")
        submitted = st.form_submit_button("Add Subscription")
        if submitted:
            if not business_name or not start_date or not end_date:
                st.error("Business name, start date, and end date are required.")
            elif start_date > end_date:
                st.error("Start date must be before end date.")
            else:
                business_id = business_options[business_name]
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO Subscriptions (business_id, start_date, end_date) VALUES (%s, %s, %s)",
                        (business_id, start_date, end_date)
                    )
                    conn.commit()
                    st.success(f"Subscription added for '{business_name}' from {start_date} to {end_date}.")
                except Exception as e:
                    st.error(f"Failed to add subscription: {e}")
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()

    # List Existing Subscriptions
    st.subheader("Existing Subscriptions")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.subscription_id, s.start_date, s.end_date, b.name AS business_name
            FROM Subscriptions s JOIN Businesses b ON s.business_id = b.business_id
            ORDER BY s.start_date
        """)
        subscriptions = cursor.fetchall()
        if subscriptions:
            for sub in subscriptions:
                st.write(f"ID: {sub['subscription_id']} | Business: {sub['business_name']} | Start: {sub['start_date']} | End: {sub['end_date']}")
        else:
            st.info("No subscriptions found.")
    finally:
        cursor.close()
        conn.close()

# --- Projects Tab ---
with tab4:
    st.header("Manage Projects and Documentation")
    
    # Add New Project and Upload XML
    st.subheader("Add New Project and Upload XML")
    with st.form("add_project_form"):
        doc_name = st.text_input("Documentation Name")
        doc_id = st.text_input("Documentation ID (unique)")
        xml_file = st.file_uploader("Upload XML File", type=["xml"])
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT business_id, name FROM Businesses ORDER BY name")
            businesses = cursor.fetchall()
            business_options = {biz['name']: biz['business_id'] for biz in businesses}
            business_name = st.selectbox("Business Name", options=list(business_options.keys()), key="proj_business")
        finally:
            cursor.close()
            conn.close()
        submitted = st.form_submit_button("Add Project and Upload")
        if submitted:
            if not doc_name or not doc_id or not xml_file or not business_name:
                st.error("Documentation name, ID, XML file, and business name are required.")
            else:
                import preprocessor  # Import here to delay PyTorch loading
                business_id = business_options[business_name]
                try:
                    # Read UploadedFile as bytes
                    xml_content = xml_file.read()
                    # Process and store XML
                    chunks = preprocessor.process_and_store_xml(xml_content, doc_id)
                    if chunks:
                        # Add to ProjectAccess
                        conn = get_db_connection()
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO ProjectAccess (business_id, doc_id, doc_name) VALUES (%s, %s, %s)",
                                (business_id, doc_id, doc_name)
                            )
                            conn.commit()
                            st.success(f"Project '{doc_name}' (ID: {doc_id}) added for '{business_name}' with {len(chunks)} chunks stored.")
                            st.write(f"Last chunk preview: {chunks[-1][:200]}...")
                        except Exception as e:
                            st.error(f"Failed to add project to ProjectAccess: {e}")
                            conn.rollback()
                        finally:
                            cursor.close()
                            conn.close()
                    else:
                        st.error("Failed to process XML file.")
                except Exception as e:
                    st.error(f"Error processing XML: {e}")

    # List Existing Projects
    st.subheader("Existing Projects")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.access_id, p.doc_id, p.doc_name, b.name AS business_name
            FROM ProjectAccess p JOIN Businesses b ON p.business_id = b.business_id
            ORDER BY p.doc_name
        """)
        projects = cursor.fetchall()
        if projects:
            for proj in projects:
                st.write(f"ID: {proj['access_id']} | Doc Name: {proj['doc_name'] or 'N/A'} | Doc ID: {proj['doc_id']} | Business: {proj['business_name']}")
        else:
            st.info("No projects found.")
    finally:
        cursor.close()
        conn.close()