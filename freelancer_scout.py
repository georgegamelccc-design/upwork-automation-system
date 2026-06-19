import os
import requests
from dotenv import load_dotenv

load_dotenv('/root/upwork-agent/.env')

TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
HEADERS = {"freelancer-oauth-v1": TOKEN}
KEYWORDS = ["python", "automation", "ai", "bot", "api", "scraping", "chatbot"]
MIN_BUDGET = 50

def get_jobs():
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {"job_details": True, "full_description": True, "limit": 50}
    try:
        r = requests.get(url, headers=HEADERS, params=params)
        data = r.json()
        if data.get("status") != "success":
            print(f"Error: {data}")
            return []
        jobs = data["result"]["projects"]
        filtered = []
        for job in jobs:
            title = job.get("title", "").lower()
            desc = job.get("description", "").lower()
            budget_min = job.get("budget", {}).get("minimum", 0) or 0
            if any(kw in title or kw in desc for kw in KEYWORDS) and budget_min >= MIN_BUDGET:
                filtered.append({
                    "title": job.get("title"),
                    "budget": f"${budget_min} - ${job.get('budget', {}).get('maximum', 0)}",
                    "bids": job.get("bid_stats", {}).get("bid_count", 0),
                    "url": f"https://www.freelancer.com/projects/{job.get('seo_url')}",
                })
        return filtered
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    print("🔍 بنسحب Jobs من Freelancer.com...")
    jobs = get_jobs()
    if not jobs:
        print("❌ مفيش jobs أو في مشكلة في الـ Token")
    else:
        print(f"✅ وجدنا {len(jobs)} job مناسبة!\n")
        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job['title']}")
            print(f"   💰 {job['budget']} | 👥 {job['bids']} bids")
            print(f"   🔗 {job['url']}\n")
