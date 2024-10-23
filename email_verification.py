import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st  # Pull creds from secrets, homie

# Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_NAME = "Contact Creation"
HUNTER_API_KEY = st.secrets["hunter"]["api_key"]  # Pull Hunter API key from secrets
HUNTER_URL = 'https://api.hunter.io/v2/email-verifier'

# Authenticate with Google Sheets API using Streamlit Secrets for service account
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_sheets"]  # Pull creds from Streamlit secrets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def run_email_verifier():
    client = get_gspread_client()  # Get Google Sheets client

    # Open the spreadsheet by name
    spreadsheet = client.open(SPREADSHEET_NAME)
    generated_sheet = spreadsheet.worksheet('Generated')  # Access by name
    validation_sheet = spreadsheet.worksheet('Validation')
    history_sheet = spreadsheet.worksheet('History')

    # Ensure header row in the "Validation" and "History" tabs
    validation_headers = ['first_name', 'last_name', 'email', 'current_company', 'current_position',
                          'about', 'skills_1', 'skills_2', 'skills_3', 'url', 'match_status', 'status', 'score']
    if not validation_sheet.row_values(1):
        validation_sheet.append_row(validation_headers)

    if not history_sheet.row_values(1):
        history_sheet.append_row(validation_headers)

    # Read data from "Generated" tab
    generated_emails = generated_sheet.get_all_values()[1:]  # Skip the header row

    # Read data from "History" tab
    history_emails = history_sheet.col_values(3)[1:]  # Skip the header row (email is in the 3rd column)
    history_emails_set = set(email.strip() for email in history_emails)

    # Filter emails to be verified, ensuring emails in the "History" tab are not verified again
    emails_to_verify = [row for row in generated_emails if row[2].strip() not in history_emails_set]

    print(f"Total generated emails: {len(generated_emails)}")
    print(f"Total emails in history: {len(history_emails_set)}")
    print(f"Total emails to verify: {len(emails_to_verify)}")

    if not emails_to_verify:
        print("No new emails to verify.")
        return "No new emails to verify."
    else:
        print("Emails to verify:")
        for email_row in emails_to_verify:
            print(email_row[2])

    # Verify emails using Hunter.io
    verification_results = []
    for email_row in emails_to_verify:
        email = email_row[2].strip()
        response = requests.get(HUNTER_URL, params={'email': email, 'api_key': HUNTER_API_KEY})
        result = response.json()
        print(f"Verifying email: {email}")
        print(f"API Response: {result}")
        if response.status_code == 200 and 'data' in result:
            verification_results.append(email_row + [result['data']['status'], result['data']['score']])
            history_emails_set.add(email)
        else:
            print(f"Error verifying email {email}: {result.get('errors', result)}")  # Log the error

    # Update "Validation" tab
    if verification_results:
        validation_sheet.append_rows(verification_results, value_input_option='RAW')

    # Update "History" tab
    if verification_results:
        history_sheet.append_rows(verification_results, value_input_option='RAW')

    # Remove checked contacts from "Generated" tab, keeping only the first row
    if verification_results:
        generated_sheet.clear()
        generated_sheet.append_row(validation_headers[:10])  # First 10 headers

    return f"{len(verification_results)} emails verified successfully!"

# Call the function
result_message = run_email_verifier()
print(result_message)

