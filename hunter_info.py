import requests
import json

# Your Hunter.io API key
API_KEY = '25d680dbe254702fa465beeffbbf41b09f3cecee'

# Function to get account information from Hunter.io
def get_hunter_account_info():
    url = "https://api.hunter.io/v2/account"
    params = {'api_key': API_KEY}
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()['data']
    else:
        raise Exception(f"Failed to retrieve data from Hunter.io API: {response.status_code}")

# Function to save the account info to a JSON file
def save_account_info():
    account_info = get_hunter_account_info()
    with open('account_info.json', 'w') as f:
        json.dump({
            'used_searches': account_info['requests']['searches']['used'],
            'used_verifications': account_info['requests']['verifications']['used']
        }, f)

# If you want to run this as a standalone script:
if __name__ == "__main__":
    save_account_info()


