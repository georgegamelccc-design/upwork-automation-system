import requests
import json
from dotenv import load_dotenv
import os

load_dotenv('/root/upwork-agent/.env')
TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")

headers = {"Freelancer-OAuth-V1": TOKEN}

# Test 1: Active projects
url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
params = {"limit": 5, "job_details": True}
r = requests.get(url, headers=headers, params=params)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2)[:2000])
