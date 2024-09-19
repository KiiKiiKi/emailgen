import csv
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# Function to clean and format company names into domains
def format_company_name(company_name):
    common_words = ['inc', 'llc', 'corp', 'corporation', 'company', 'limited']
    clean_name = re.sub(r'[^a-zA-Z\s]', '', company_name).lower()
    words = clean_name.split()
    words = [word for word in words if word not in common_words]
    domain_name = '.'.join(words)
    return domain_name

# Function to generate email based on a given pattern and domain
def generate_email_from_pattern(first_name, last_name, pattern, domain):
    if not first_name:  # Handle empty first_name
        first_name = "unknown"
    first_initial = first_name[0] if first_name else ""
    email = (pattern
             .replace('{first}', first_name)
             .replace('{last}', last_name)
             .replace('{f}', first_initial)
             .replace('{firstinitial}', first_initial)
             .replace('{firstname}', first_name)
             .replace('{lastname}', last_name)
             .replace('{domain}', domain))
    return email

# Read Contacts CSV file and handle BOM
with open('contacts.csv', mode='r', encoding='utf-8-sig') as file:
    reader = csv.DictReader(file)
    print("Headers found in contacts.csv:", reader.fieldnames)  # Debugging line to print headers
    contacts = [row for row in reader]

# Read Email Structures CSV file and handle BOM
with open('email_structures.csv', mode='r', encoding='utf-8-sig') as file:
    reader = csv.DictReader(file)
    print("Headers found in email_structures.csv:", reader.fieldnames)  # Debugging line to print headers
    email_structures = {format_company_name(row['Organization']): (row['email_pattern'], row['domain']) for row in reader}

# Function to find the best match for a company name using fuzzy matching
def find_best_match(company_name, email_structures):
    formatted_name = format_company_name(company_name)
    matches = process.extract(formatted_name, email_structures.keys(), scorer=fuzz.token_sort_ratio)
    if matches and matches[0][1] > 80:  # Adjust the threshold as needed
        return email_structures[matches[0][0]]
    return None

# Generate emails without validation
output_emails = []
for contact in contacts:
    first_name = contact['first_name'].lower()
    last_name = contact['last_name'].lower()
    company = contact['company']
    first_initial = first_name[0] if first_name else ""
    
    result = find_best_match(company, email_structures)
    
    if result:
        pattern, domain = result
        print(f"Debug: first_name={first_name}, last_name={last_name}, pattern={pattern}, domain={domain}")  # Debugging line
        email = generate_email_from_pattern(first_name, last_name, pattern, domain)
        match_status = "Match!"
    else:
        formatted_domain = format_company_name(company) + '.com'
        patterns = [
            f"{first_name}.{last_name}@{formatted_domain}",
            f"{first_name}_{last_name}@{formatted_domain}",
            f"{first_name}@{formatted_domain}",
            f"{first_name}{last_name}@{formatted_domain}",
            f"{first_initial}.{last_name}@{formatted_domain}"
        ]
        email = patterns[0]  # Just pick the first pattern for simplicity
        match_status = "Unmatched :("

    output_emails.append({
        'first_name': contact['first_name'],
        'last_name': contact['last_name'],
        'company': company,
        'email': email,
        'match_status': match_status
    })

# Write the output to a CSV file
with open('generated_emails.csv', mode='w', newline='') as file:
    fieldnames = ['first_name', 'last_name', 'company', 'email', 'match_status']
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    
    writer.writeheader()
    for row in output_emails:
        writer.writerow(row)

print("Generated emails saved to 'generated_emails.csv'")
