import os
import requests
from dotenv import load_dotenv
from proposal_writer import write_proposal

load_dotenv('/root/upwork-agent/.env')

TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
HEADERS = {"Freelancer-OAuth-V1": TOKEN}

def get_jobs(keywords="python automation", limit=5):
    url = "https://www.freelancer.com/api/projects/0.1/projects/active/"
    params = {
        "query": keywords,
        "limit": limit,
        "full_description": True,
        "job_details": True
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    data = resp.json()
    jobs = data.get("result", {}).get("projects", [])
    return jobs

def score_job(job):
    score = 0
    budget = job.get("budget", {})
    minimum = budget.get("minimum", 0)
    if minimum >= 100: score += 30
    if minimum >= 500: score += 20
    bid_count = job.get("bid_stats", {}).get("bid_count", 99)
    if bid_count < 10: score += 30
    if bid_count < 5:  score += 20
    return score

if __name__ == "__main__":
    print("🔍 بندور على Jobs...")
    jobs = get_jobs("python automation", limit=5)
    print(f"✅ لقينا {len(jobs)} Job\n")
    
    for job in jobs:
        score = score_job(job)
        title = job.get("title", "")
        budget = job.get("budget", {})
        min_b = budget.get("minimum", 0)
        max_b = budget.get("maximum", 0)
        bids = job.get("bid_stats", {}).get("bid_count", 0)
        
        print(f"📋 {title}")
        print(f"   💰 ${min_b} - ${max_b} | 👥 {bids} bids | ⭐ Score: {score}/100")
        
        if score >= 50:
            print("   ✍️  بنكتب Proposal...")
            desc = job.get("description", "")[:500]
            proposal = write_proposal(title, desc, f"${min_b}-${max_b}", "Freelancer")
            print(f"   📝 Proposal:\n{proposal[:200]}...")
        else:
            print("   ⏭️  Score منخفض — بنتخطاه")
        print("-" * 60)
