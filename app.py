import streamlit as st
import json
import time
from hunter_info import save_account_info  # Import the function from hunter_info.py
from email_generator import run_email_generator  # Import your email generator
from email_verifier import run_email_verifier  # Import your email verifier

# Read account info from JSON file
def read_account_info():
    with open('account_info.json', 'r') as f:
        return json.load(f)

# Function to refresh the usage values dynamically
def refresh_usage_values():
    save_account_info()  # Directly call the function to get account info
    account_info = read_account_info()  # Read the updated account info
    return account_info.get('used_searches', 'N/A'), account_info.get('used_verifications', 'N/A')

# Create the Streamlit interface
st.markdown("""
    <style>
    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
    }
    .full-width {
        width: calc(100vw - 40px); /* 20px padding on each side */
        margin-left: calc(-50vw + 20px);
        left: 50%;
        position: relative;
        background-color: #E8E8E8;
        padding: 20px;
        box-sizing: border-box;
    }
    .container {
        max-width: 1200px;
        margin: auto;
        padding: 20px;
    }
    .title {
        font-size: 32px;
        font-weight: bold;
        color: #000;
    }
    .stats {
        font-size: 18px;
        color: #333;
        text-align: right;
    }
    .stats .number {
        color: #27C490;
    }
    .section-header {
        font-size: 18px;
        color: #888;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .stButton button {
        font-size: 18px;
        padding: 10px 20px;
        background-color: #2C4D5C !important;
        color: white !important;
        border: none;
        border-radius: 20px;
        margin: 10px 0;
        transition: background-color 0.3s;
    }
    .stButton button:hover {
        background-color: #27C490 !important;
        color: white !important;
    }
    .link {
        font-size: 18px;
        color: #1e3a5f;
        text-decoration: none;
    }
    .footer {
        width: calc(100vw - 40px); /* 20px padding on each side */
        margin-left: calc(-50vw + 20px);
        left: 50%;
        position: relative;
        background-color: #E8E8E8;
        font-size: 14px;
        color: #888;
        text-align: center;
        margin-top: 20px;
        padding: 20px;
        box-sizing: border-box;
    }
    </style>
""", unsafe_allow_html=True)

# Header
header_placeholder = st.empty()

# Main Content
st.markdown('<div class="container">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="section-header">LinkedIn Contact Extraction</div>', unsafe_allow_html=True)
    if st.button('Run Email Generator'):
        with st.spinner('Running Email Generator...'):
            result = run_email_generator()  # Call the email generator directly
        st.write(result)
        st.success('Email Generator completed!')

    if st.button('Run Email Verifier'):
        with st.spinner('Running Email Verifier...'):
            result = run_email_verifier()  # Call the email verifier directly
        st.write(result)
        st.success('Email Verifier completed!')

    st.markdown('<a href="https://docs.google.com/spreadsheets/d/1pNhTLbKGcbmpvCIs6upg3f9RxpOlH1XfKc4bpDDhnFA/edit?usp=sharing"> Link to Contact Creation Sheet</a>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="section-header">Hunter.io Features</div>', unsafe_allow_html=True)
    st.markdown('<a href="https://hunter.io/search" target="_blank"><button class="stButton">Domain Search</button></a>', unsafe_allow_html=True)
    st.markdown('<a href="https://hunter.io/verify" target="_blank"><button class="stButton">Bulk Email Verification</button></a>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="full-width">
    <div class="footer">
        Any questions? <a href="https://ambiguous-pleasure-22d.notion.site/Creating-new-contacts-for-QED-Send-Outs-c887c5e75b7441e4ba879697bc5d2a8a?pvs=4" class="link">Click here for the full documentation</a>
    </div>
</div>
""", unsafe_allow_html=True)

# Periodically refresh the usage values
while True:
    used_searches, used_verifications = refresh_usage_values()
    header_placeholder.markdown(f"""
    <!-- Your HTML code for displaying the stats -->
    Domain Searches Used: {used_searches}<br>
    Verifications Used: {used_verifications}
    """, unsafe_allow_html=True)
    time.sleep(30)



