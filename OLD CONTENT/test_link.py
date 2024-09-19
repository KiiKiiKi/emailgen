import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('E:\Scripts\email_generator\service-account.json', scope)
client = gspread.authorize(creds)

# Open the spreadsheet by name
spreadsheet = client.open("Contact Creation")

# Access the first worksheet by index (0)
extract_sheet = spreadsheet.get_worksheet(0)  # "Extract" tab

# Test reading data
contacts = extract_sheet.get_all_records()
print(contacts)
