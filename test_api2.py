import requests
import json
from dotenv import load_dotenv
import os

load_dotenv('/root/upwork-agent/.env')
TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
headers = {"Freelancer-OAuth-V1": TOKEN}

# Search endpoint الصح
url = "https://www.freelancer.com/api/projects/0.1/projects/"
params = {
    "limit": 10,
    "offset": 0,
    "project_types[]": "fixed",
    "or_search_query": "n8n automation workflow AI integration make zapier",
    "full_description": True,
    "job_details": True,
    "sort_field": "time_updated",
    "reverse_sort": True
}

r = requests.get(url, headers=headers, params=params)
print(f"Status: {r.status_code}")
data = r.json()

projects = data.get("result", {}).get("projects", [])
print(f"Found: {len(projects)} projects\n")

for p in projects[:5]:
    print(f"📋 {p.get('title')}")
    print(f"   💰 ${p.get('budget', {}).get('minimum',0)} - ${p.get('budget', {}).get('maximum',0)}")
    print(f"   🔗 https://www.freelancer.com/projects/{p.get('seo_url', p.get('id'))}")
    print()
