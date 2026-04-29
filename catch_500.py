import requests
import json

API_URL = "http://localhost:8080/api/v1/query"

test_case = {
    "domain": "operations",
    "query": "Is there a correlation between user age and transaction failure rates? Compare failure percentages for users above and below 40 years old."
}

try:
    response = requests.post(API_URL, json=test_case)
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print("Response Body:")
        print(response.text)
    else:
        print("Success!")
        print(json.dumps(response.json(), indent=2)[:500])
except Exception as e:
    print(f"Error: {e}")
