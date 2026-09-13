import requests
import json

# Test the upload endpoint
url = "http://127.0.0.1:8000/reviews"
files = {'file': open('test_data.csv', 'rb')}
data = {'company': 'Apple'}

try:
    response = requests.post(url, files=files, data=data, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
finally:
    files['file'].close()
