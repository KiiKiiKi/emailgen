import re
import unidecode
from fuzzywuzzy import fuzz, process
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Function to clean and format company names into domains
def format_company_name(company_name):
    if not isinstance(company_name, str):
        return ''
    common_words = ['inc', 'llc', 'corp', 'corporation', 'company', 'limited', 'ltd']
    clean_name = re.sub(r'[^a-zA-Z\s]', '', unidecode.unidecode(company_name)).lower()
    words = clean_name.split()
    words = [word for word in words if word not in common_words]
    domain_name = ''.join(words)  # Remove spaces and join words without punctuation
    return domain_name

# Function to remove accents and special characters from names
def clean_name(name):
    clean_name = re.sub(r'[^a-zA-Z]', '', unidecode.unidecode(name))
    return clean_name.lower()

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('E:/Scripts/email_generator/service-account.json', scope)
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

# Function to generate email based on a given pattern and domain
def generate_email_from_pattern(first_name, last_name, pattern, domain):
    if not first_name:  # Handle empty first_name
        first_name = "unknown"
    if not last_name:  # Handle empty last_name
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

# Function to find the best match for a company name using fuzzy matching
def find_best_match(company_name, email_structures):
    formatted_name = format_company_name(company_name)
    matches = process.extract(formatted_name, email_structures.keys(), scorer=fuzz.token_sort_ratio)
    if matches and matches[0][1] > 80:  # Adjusted the threshold to 80
        return email_structures[matches[0][0]]
    return None

# Split names and generate emails
output_emails = []
contacts = extract_sheet.get_all_records()

if len(contacts) > 1:
    headers = contacts[0]
    contacts = contacts[1:]  # Skip the first row (headers)
else:
    headers = []

for contact in contacts:
    full_name = contact['Name']
    name_parts = full_name.split()
    original_first_name = name_parts[0]
    original_last_name = name_parts[1] if len(name_parts) > 1 else ""  # Handle single-part names
    cleaned_first_name = clean_name(original_first_name)
    cleaned_last_name = clean_name(original_last_name)
    company = contact['Current company']
    first_initial = cleaned_first_name[0] if cleaned_first_name else ""
    
    result = find_best_match(company, email_structures)
    
    if result:
        pattern, domain = result
        email = generate_email_from_pattern(cleaned_first_name, cleaned_last_name, pattern, domain)
        match_status = "Match!"
    else:
        formatted_domain = format_company_name(company) + '.com'
        patterns = [
            f"{cleaned_first_name}.{cleaned_last_name}@{formatted_domain}",
            f"{cleaned_first_name}_{cleaned_last_name}@{formatted_domain}",
            f"{cleaned_first_name}@{formatted_domain}",
            f"{cleaned_first_name}{cleaned_last_name}@{formatted_domain}",
            f"{first_initial}.{cleaned_last_name}@{formatted_domain}"
        ]
        email = patterns[0]  # Just pick the first pattern for simplicity
        match_status = "Unmatched :("

    output_emails.append({
        'first_name': original_first_name,
        'last_name': original_last_name,
        'email': email,
        'current_company': company,
        'current_position': contact['Current position'],
        'about': contact['About'],
        'skills_1': contact['Skills 1'],
        'skills_2': contact['Skills 2'],
        'skills_3': contact['Skills 3'],
        'url': contact['url'],
        'match_status': match_status
    })

# Write the output to Google Sheets
output_data = [[row['first_name'], row['last_name'], row['email'], row['current_company'], row['current_position'], row['about'], row['skills_1'], row['skills_2'], row['skills_3'], row['url'], row['match_status']] for row in output_emails]

if output_data:
    generated_sheet.append_rows(output_data, table_range='A2')

# Clear the Extract sheet, except the header row
extract_headers = extract_sheet.row_values(1)
extract_sheet.clear()
extract_sheet.append_row(extract_headers)








