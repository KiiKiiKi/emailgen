import requests
import json

# Your Hunter.io API key
API_KEY = '25d680dbe254702fa465beeffbbf41b09f3cecee'

# Function to get account information from Hunter.io
def get_hunter_account_info(api_key):
    url = "https://api.hunter.io/v2/account"
    params = {
        'api_key': api_key
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print("API Response:", json.dumps(data, indent=4))  # Print the entire response for debugging
        return data['data']
    else:
        raise Exception(f"Failed to retrieve data from Hunter.io API: {response.status_code}")

def save_account_info():
    account_info = get_hunter_account_info(API_KEY)
    
    if account_info and 'requests' in account_info:
        print("Requests found in account_info")
        searches_info = account_info['requests'].get('searches', {})
        verifications_info = account_info['requests'].get('verifications', {})
        
        print("Searches Info:", searches_info)
        print("Verifications Info:", verifications_info)
        
        used_searches = searches_info.get('used', 'N/A')
        used_verifications = verifications_info.get('used', 'N/A')
    else:
        print("Requests not found in account_info or account_info is None")
        used_searches = 'N/A'
        used_verifications = 'N/A'

    info = {
        'used_searches': used_searches,
        'used_verifications': used_verifications
    }

    print("Info to be saved:", info)  # Print the info dictionary before saving

    with open('account_info.json', 'w') as f:
        json.dump(info, f)

if __name__ == "__main__":
    save_account_info()
