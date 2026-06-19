import requests
import json
from dotenv import load_dotenv
import os

load_dotenv('/root/upwork-agent/.env')
TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
headers = {"Freelancer-OAuth-V1": TOKEN}

# نفس الـ endpoint اللي اشتغل قبل كده
url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
params = {
    "limit": 20,
    "job_details": True,
    "full_description": True
}

r = requests.get(url, headers=headers, params=params)
print(f"Status: {r.status_code}")
data = r.json()
projects = data.get("result", {}).get("projects", [])
print(f"Total projects: {len(projects)}\n")

# فلتر يدوي بالكلمات
keywords = ["n8n", "automation", "workflow", "AI", "zapier", "make.com", 
            "integration", "bot", "api", "chatbot", "openai", "gpt", "automate"]

matched = []
for p in projects:
    title = (p.get("title") or "").lower()
    desc = (p.get("description") or "").lower()
    text = title + " " + desc
    if any(kw.lower() in text for kw in keywords):
        matched.append(p)

print(f"Matched projects: {len(matched)}\n")
for p in matched[:5]:
    print(f"📋 {p.get('title')}")
    print(f"   💰 ${p.get('budget', {}).get('minimum',0)} - ${p.get('budget', {}).get('maximum',0)}")
    print(f"   🔗 https://www.freelancer.com/projects/{p.get('seo_url', p.get('id'))}")
    print()

# لو مفيش matched، اطبع أول 5 projects عشان نشوف إيه الموجود
if not matched:
    print("--- أول 5 projects موجودة ---")
    for p in projects[:5]:
        print(f"📋 {p.get('title')}")
