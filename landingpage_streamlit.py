import streamlit as st

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        background-color: #2563eb;
        color: white;
        padding: 2rem;
        text-align: center;
        border-radius: 0.5rem;
    }
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .main-header p {
        font-size: 1.25rem;
        margin-top: 0.5rem;
    }
    .hero-section {
        background-color: white;
        padding: 3rem 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .hero-text h2 {
        font-size: 2rem;
        font-weight: bold;
        color: white;
    }
    .hero-text p {
        color: white;
        margin: 1rem 0;
    }
    .feature-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 1rem 0;
    }
    .feature-card h3 {
        font-size: 1.25rem;
        font-weight: bold;
        color: #1f2937;
    }
    .feature-card p {
        color: #4b5563;
        margin-top: 0.5rem;
    }
    .cta-section {
        background-color: #2563eb;
        color: white;
        padding: 3rem 1rem;
        text-align: center;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .cta-section h2 {
        font-size: 2rem;
        font-weight: bold;
    }
    .cta-section p {
        font-size: 1.25rem;
        margin: 1rem 0;
    }
    .footer {
        background-color: #1f2937;
        color: white;
        padding: 1.5rem;
        text-align: center;
        margin-top: 1rem;
    }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 0.375rem;
        border: none;
        font-size: 1rem;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
    <div class="main-header">
        <h1>AI Helpdesk Beta</h1>
        <p>AI-Powered Chatbot for Your Business</p>
    </div>
""", unsafe_allow_html=True)

# Hero Section
col1, = st.columns([1])
with col1:
    st.markdown("""
        <div class="hero-text">
            <h2>Revolutionize Your Business Communication</h2>
            <p>AI Helpdesk provides a secure, subscription-based AI chatbot for your team to access project-specific information instantly via Telegram.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("Try the Beta Now"):
        st.markdown("[Join AI Helpdesk on Telegram](https://t.me/helpdesk_chatbot)")



st.markdown("<h2 style='text-align: center; font-size: 2rem; font-weight: bold; color: white;'>Key Features</h2>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
        <div class="feature-card">
            <h3>Subscription-Based Access</h3>
            <p>Flexible plans for businesses, with access for all employees during the subscription period.</p>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
        <div class="feature-card">
            <h3>Project-Specific Queries</h3>
            <p>Employees can only access information for projects assigned to their company.</p>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
        <div class="feature-card">
            <h3>Session Logging & Support</h3>
            <p>Logs unresolved queries and sends summaries to human support for follow-up.</p>
        </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Call-to-Action Section
st.markdown("""
    <div class="cta-section">
        <h2>Ready to Get Started?</h2>
        <p>Join the beta and experience seamless business communication.</p>
    </div>
""", unsafe_allow_html=True)
if st.button("Join Beta", key="cta_button"):
    st.markdown("[Join AI Helpdesk on Telegram](https://t.me/helpdesk_chatbot)")

# Footer
st.markdown("""
    <div class="footer">
        <p>© 2025 AI Helpdesk. All rights reserved.</p>
        <p>Contact: support@company.com</p>
    </div>
""", unsafe_allow_html=True)