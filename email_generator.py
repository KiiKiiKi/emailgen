import re
import unidecode
from fuzzywuzzy import fuzz, process
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st  # Import Streamlit for secrets
import logging

# Setup logging to capture issues
logging.basicConfig(level=logging.INFO)

# Function to clean and format company names into domains
def format_company_name(company_name):
    if not isinstance(company_name, str):
        return ''
    common_words = ['inc', 'llc', 'corp', 'corporation', 'company', 'limited', 'ltd']
    clean_name = re.sub(r'[^a-zA-Z\s]', '', unidecode.unidecode(company_name)).lower()
    words = clean_name.split()
    words = [word for word in words if word not in common_words]
    domain_name = ''.join(words)
    return domain_name

# Function to remove accents and special characters from names
def clean_name(name):
    clean_name = re.sub(r'[^a-zA-Z]', '', unidecode.unidecode(name))
    return clean_name.lower()

# Function to run the email generator logic
def run_email_generator():
    # Google Sheets setup - now using Streamlit secrets instead of local file
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_sheets"]  # Pull creds from Streamlit secrets
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # Open the spreadsheet by name
    spreadsheet = client.open("Contact Creation")
    extract_sheet = spreadsheet.get_worksheet(0)  # "Extract" tab
    generated_sheet = spreadsheet.get_worksheet(1)  # "Generated" tab
    email_patterns_sheet = spreadsheet.worksheet("Email Patterns")  # "Email Patterns" tab

    # Load email structures from the "Email Patterns" tab
    email_structures = {}
    email_patterns = email_patterns_sheet.get_all_records()

    for row in email_patterns:
        if 'domain' in row and 'email_pattern' in row and 'Organization' in row:
            domain_name = row['domain']
            email_pattern = row['email_pattern']
            organization = row['Organization']
            if organization and isinstance(organization, str):  # Ensure organization is not None and is a string
                organization = format_company_name(organization)
                email_structures[organization] = (email_pattern, domain_name)

    # Get all contacts from the "Extract" sheet
    contacts = extract_sheet.get_all_records()

    # Now we assume that the first row is always the header
    if contacts:
        headers = contacts[0]  # This is the header row
        contacts = contacts[1:]  # Process everything from row 2 onward

    # Split names and generate emails
    output_emails = []

    for idx, contact in enumerate(contacts):
        try:
            full_name = contact.get('Name', '').strip()
            company = contact.get('Current company', '').strip()

            if not full_name or not company:  # Handle empty name or company gracefully
                logging.warning(f"Row {idx + 2} skipped: Missing name or company. Name: {full_name}, Company: {company}")
                continue

            # Ensure the name is processed even if partially missing
            name_parts = full_name.split()
            original_first_name = name_parts[0] if len(name_parts) > 0 else "unknown"
            original_last_name = name_parts[1] if len(name_parts) > 1 else "unknown"

            cleaned_first_name = clean_name(original_first_name)
            cleaned_last_name = clean_name(original_last_name)
            first_initial = cleaned_first_name[0] if cleaned_first_name else ""

            # Find the best match for the company
            result = find_best_match(company, email_structures)

            if result:
                pattern, domain = result
                email = generate_email_from_pattern(cleaned_first_name, cleaned_last_name, pattern, domain)
                match_status = "Match!"
            else:
                # Fallback email generation if unmatched
                formatted_domain = format_company_name(company) + '.com'
                patterns = [
                    f"{cleaned_first_name}.{cleaned_last_name}@{formatted_domain}",
                    f"{cleaned_first_name}_{cleaned_last_name}@{formatted_domain}",
                    f"{cleaned_first_name}@{formatted_domain}",
                    f"{cleaned_first_name}{cleaned_last_name}@{formatted_domain}",
                    f"{first_initial}.{cleaned_last_name}@{formatted_domain}"
                ]
                email = patterns[0]  # Pick the first pattern as fallback
                match_status = "Unmatched :("

            # Append contact email data to output list
            output_emails.append({
                'first_name': original_first_name,
                'last_name': original_last_name,
                'email': email,
                'current_company': company,
                'current_position': contact.get('Current position', ''),
                'about': contact.get('About', ''),
                'skills_1': contact.get('Skills 1', ''),
                'skills_2': contact.get('Skills 2', ''),
                'skills_3': contact.get('Skills 3', ''),
                'url': contact.get('url', ''),
                'match_status': match_status
            })

        except Exception as e:
            # Log any errors and continue with the next contact
            logging.error(f"Error processing row {idx + 2}: {e}")
            continue

    # Prepare data for Google Sheets bulk append
    output_data = [[row['first_name'], row['last_name'], row['email'], row['current_company'], row['current_position'], row['about'], row['skills_1'], row['skills_2'], row['skills_3'], row['url'], row['match_status']] for row in output_emails]

    # Write all generated emails to Google Sheets at once
    if output_data:
        generated_sheet.append_rows(output_data, table_range='A2')

    # Clear the Extract sheet, except the header row
    extract_headers = extract_sheet.row_values(1)
    extract_sheet.clear()
    extract_sheet.append_row(extract_headers)

    return f"{len(output_emails)} emails generated successfully!"  # Return a message for Streamlit to display

# Helper functions (put these at the top if they are referenced elsewhere)
def generate_email_from_pattern(first_name, last_name, pattern, domain):
    if not first_name:  
        first_name = "unknown"
    if not last_name:  
        last_name = "unknown"
    first_initial = first_name[0] if first_name else ""
    last_initial = last_name[0] if last_name else ""
    email = (pattern
             .replace('{first}', first_name)
             .replace('{last}', last_name)
             .replace('{f}', first_initial)
             .replace('{firstinitial}', first_initial)
             .replace('{firstname}', first_name)
             .replace('{lastname}', last_name)
             .replace('{lastinitial}', last_initial)
             .replace('{domain}', domain))
    return email

def find_best_match(company_name, email_structures):
    formatted_name = format_company_name(company_name)
    
    # Filter out email structures with 'Unmatched' as the pattern
    valid_email_structures = {org: val for org, val in email_structures.items() if val[0] != 'Unmatched'}
    
    # Find the best matches using fuzzy matching
    matches = process.extract(formatted_name, valid_email_structures.keys(), scorer=fuzz.token_sort_ratio)
    
    # Check for valid matches above a certain threshold
    if matches:
        # Sort the matches by their similarity score in descending order
        matches = sorted(matches, key=lambda x: x[1], reverse=True)
        
        # Return the first valid match (score > 80) or None if no valid match is found
        for match in matches:
            if match[1] > 80:
                return email_structures.get(match[0])
    
    return None










