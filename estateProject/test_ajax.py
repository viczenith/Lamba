import requests
import json

# Test the AJAX form submission
url = 'http://127.0.0.1:8000/user-registration/'

# Simulate form data
data = {
    'name': 'Test User',
    'email': 'test@example.com',
    'phone': '+1234567890',
    'address': '123 Test St',
    'country': 'Nigeria',
    'role': 'admin',
    'password': 'testuser123',
    'source': 'company_profile',
    'csrfmiddlewaretoken': 'dummy'  # This would be real in browser
}

headers = {
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded'
}

try:
    response = requests.post(url, data=data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    if response.headers.get('content-type') == 'application/json':
        print("JSON Response:", json.loads(response.text))
except Exception as e:
    print(f"Error: {e}")