import requests
import json
import statistics

# Set the API endpoint
API_URL = "http://localhost:8080/api/v1/query"

DEEP_ANALYSIS_QUESTIONS = [
    {
        "domain": "operations",
        "query": "Is there a correlation between user age and transaction failure rates? Compare failure percentages for users above and below 40 years old."
    },
    {
        "domain": "risk",
        "query": "What is the concentration of HIGH and CRITICAL risk users across different cities? Identify the top 3 cities with the highest risk profile."
    },
    {
        "domain": "operations",
        "query": "Analyze the impact of login failures on transaction status. Compare the percentage of successful transactions for users with at least one failed login vs those with none."
    },
    {
        "domain": "compliance",
        "query": "Compare transaction volumes and total values for PEP vs non-PEP users to identify if PEP status influences trading behavior."
    },
    {
    "domain": "security",
    "query": "Identify users who have logged in from more than 2 different countries and check if they have any FLAGGED transactions."
    }
]

def run_tests():
    print("🚀 Starting Deep Analysis Tests...\n")
    
    for i, test_case in enumerate(DEEP_ANALYSIS_QUESTIONS, 1):
        print(f"Test Case {i}: {test_case['query']}")
        print(f"Domain: {test_case['domain']}")
        
        try:
            response = requests.post(
                API_URL,
                json=test_case,
                timeout=90
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {data.get('status')}")
                
                if data.get('status') == 'success':
                    print(f"SQL: {data.get('sql')}")
                    print(f"First Result Row: {data.get('results')[0] if data.get('results') else 'No results'}")
                    print(f"Insight: {data.get('insight')}")
                    print(f"Recommendation: {data.get('recommendation')}")
                elif data.get('status') == 'needs_clarification':
                    print(f"Clarification Needed: {data.get('clarification_question')}")
                else:
                    print(f"Error: {data.get('error') or 'Unknown failure'}")
            else:
                print(f"Failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {str(e)}")
            
        print("-" * 50 + "\n")
        import time
        time.sleep(3) # Wait between tests

if __name__ == "__main__":
    run_tests()
