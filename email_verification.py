import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests

# Access the Hunter.io API key
HUNTER_API_KEY = st.secrets["hunter"]["api_key"]

# Access Google Service Account credentials
SERVICE_ACCOUNT_INFO = st.secrets["google_sheets"]

# Configuration
SPREADSHEET_NAME = "Contact Creation"
HUNTER_URL = 'https://api.hunter.io/v2/email-verifier'

def run_email_verifier():
    # Quick API check (Hunter.io)
    test_email = "example@example.com"
    params = {'email': test_email, 'api_key': HUNTER_API_KEY}

    try:
        response = requests.get(HUNTER_URL, params=params)
        if response.status_code == 200 and 'data' in response.json():
            print("Hunter.io API connection ✅")
        else:
            print(f"⚠️ Hunter.io API connection issue. Status: {response.status_code}, Response: {response.text}")
            return  # Stop if API is unreachable

# Authenticate with Google Sheets API
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(SERVICE_ACCOUNT_INFO), scope)
    client = gspread.authorize(creds)
    return client

def run_email_verifier():
    try:
        print("Starting email verification...")
        client = get_gspread_client()
        print("Authenticated with Google Sheets.")

        # Open the spreadsheet by name
        spreadsheet = client.open(SPREADSHEET_NAME)
        print(f"Opened spreadsheet: {SPREADSHEET_NAME}")

        # Access the sheets by name
        generated_sheet = spreadsheet.worksheet('Generated')
        validation_sheet = spreadsheet.worksheet('Validation')
        history_sheet = spreadsheet.worksheet('History')

        # Ensure header rows in the "Validation" and "History" tabs
        validation_headers = ['first_name', 'last_name', 'email', 'current_company', 'current_position',
                              'about', 'skills_1', 'skills_2', 'skills_3', 'url', 'match_status', 'status', 'score']
        if not validation_sheet.row_values(1):
            validation_sheet.append_row(validation_headers)

        if not history_sheet.row_values(1):
            history_sheet.append_row(validation_headers)

        # Read data from "Generated" tab
        data = generated_sheet.get_all_values()
        if not data or len(data) == 1:
            print("No data found in 'Generated' sheet.")
            return

        headers = data[0]
        rows = data[1:]  # Exclude the header row

        # Find the index of the 'email' column
        try:
            email_col_index = headers.index('email')
        except ValueError:
            print("'email' column not found in 'Generated' sheet.")
            return

        # Read emails from "History" tab to avoid re-verifying
        history_data = history_sheet.get_all_values()[1:]  # Skip header
        history_email_index = validation_headers.index('email')
        history_emails = [row[history_email_index].strip() for row in history_data if len(row) > history_email_index]
        history_emails_set = set(history_emails)

        # Collect rows to verify, skipping emails already in history
        rows_to_verify = []
        for row in rows:
            if len(row) > email_col_index:
                email = row[email_col_index].strip()
                if email and email not in history_emails_set:
                    rows_to_verify.append(row)
                else:
                    if not email:
                        print(f"Empty email in row: {row}")
                    else:
                        print(f"Email {email} already in history. Skipping.")
            else:
                print(f"No email found in row: {row}")

        if not rows_to_verify:
            print("No new emails to verify.")
            return

        print(f"Total new emails to verify: {len(rows_to_verify)}")

        # Verify emails using Hunter.io
        verification_results = []
        for row in rows_to_verify:
            email = row[email_col_index].strip()
            print(f"Verifying email: {email}")
            params = {
                'email': email,
                'api_key': HUNTER_API_KEY
            }
            response = requests.get(HUNTER_URL, params=params)
            print(f"HTTP Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")

            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON for email {email}: {e}")
                continue

            if 'data' in result:
                status = result['data'].get('status', 'unknown')
                score = result['data'].get('score', 'unknown')
                print(f"Email: {email}, Status: {status}, Score: {score}")
                # Append the full row data along with status and score
                verification_results.append(row + [status, score])
                history_emails_set.add(email)
            elif 'errors' in result:
                print(f"Error verifying email {email}: {result['errors']}")
            else:
                print(f"Unexpected response for email {email}: {result}")

        print(f"{len(verification_results)} emails verified successfully!")

        # Update "Validation" tab
        if verification_results:
            validation_sheet.append_rows(verification_results, value_input_option='RAW')
            print("Updated 'Validation' sheet.")

        # Update "History" tab
        if verification_results:
            history_sheet.append_rows(verification_results, value_input_option='RAW')
            print("Updated 'History' sheet.")

        # Remove verified contacts from "Generated" tab, keeping only the header row
        if verification_results:
            generated_sheet.clear()
            generated_sheet.append_row(headers)
            print("Cleared 'Generated' sheet and restored header row.")

    except Exception as e:
        print(f"An error occurred: {e}")

if st.button("Run Email Verifier"):
    run_email_verifier()


