import os, requests, json, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/root/upwork-agent/.env')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FREELANCER_TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"})
    except:
        print(f"Telegram error")

def get_jobs():
    headers = {"Freelancer-OAuth-V1": FREELANCER_TOKEN}
    params = {"limit": 50, "job_details": True, "full_description": True}
    r = requests.get("https://www.freelancer.com/api/projects/0.1/projects/active/", headers=headers, params=params)
    if r.status_code != 200:
        return []
    return r.json().get("result", {}).get("projects", [])

def score_job(title, description):
    title = (title or "").lower()
    desc = (description or "").lower()
    text = title + " " + desc
    
    # كلمات أساسية - score عالي
    core = ["n8n", "make.com", "zapier", "automation workflow", "ai automation", 
            "workflow automation", "automate", "openai api", "chatbot build",
            "ai agent", "ai integration", "gpt integration"]
    
    # كلمات ثانوية - score متوسط  
    secondary = ["api integration", "workflow", "automation", "bot", "ai", 
                 "integration", "crm automation", "email automation"]
    
    score = 0
    for kw in core:
        if kw in text:
            score += 25
    for kw in secondary:
        if kw in text:
            score += 10
    
    # حذف لو في keywords مش مناسبة
    exclude = ["video", "design", "logo", "seo", "writing", "translation", 
               "legal", "accounting", "photo", "music", "3d", "animation"]
    for ex in exclude:
        if ex in text:
            score -= 30
    
    return max(0, min(score, 100))

def write_proposal(title, description, budget):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"""
Write a short, professional freelance proposal (max 150 words).
You are an expert in n8n workflows, AI automation, and API integrations.

Job: {title}
Details: {description[:400]}
Budget: ${budget}

Rules:
- Start with a specific hook about THEIR problem
- Show you understand exactly what they need
- Mention relevant tech (n8n, AI, API, etc.)
- Propose clear solution in 1-2 sentences
- End with confident CTA
- No generic phrases like "I hope this finds you well"
- Write in English, conversational tone
"""}]
    )
    return response.choices[0].message.content

def run():
    print("🚀 Starting Master System...")
    send_telegram("🤖 <b>Agent Started</b>\n🔍 Scanning Freelancer.com...")
    
    jobs = get_jobs()
    print(f"Total jobs fetched: {len(jobs)}")
    
    # Score كل job
    scored = []
    for j in jobs:
        score = score_job(j.get("title",""), j.get("description",""))
        if score >= 30:
            scored.append((j, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:3]
    
    print(f"Good matches: {len(scored)} → Sending top {len(top)}")
    send_telegram(f"📊 Found <b>{len(jobs)}</b> jobs → <b>{len(scored)}</b> matches → Sending top <b>{len(top)}</b>")
    
    if not top:
        send_telegram("😴 No strong matches now. Will retry later.")
        return
    
    for job, score in top:
        budget_min = job.get('budget', {}).get('minimum', 0)
        budget_max = job.get('budget', {}).get('maximum', 0)
        budget = f"{budget_min}-{budget_max}"
        title = job.get('title', '')
        desc = job.get('description', '')
        url = f"https://www.freelancer.com/projects/{job.get('seo_url', job.get('id'))}"
        
        print(f"Writing proposal for: {title} ({score}/100)")
        proposal = write_proposal(title, desc, budget)
        
        stars = "⭐" * (score // 25)
        msg = f"""{stars} <b>Score: {score}/100</b>

📋 <b>{title}</b>
💰 ${budget}
🔗 {url}

✍️ <b>Proposal Ready:</b>
{proposal}

━━━━━━━━━━━━━━━━━━━
👆 انسخ وابعته على Freelancer"""
        
        send_telegram(msg)
        print(f"✅ Sent to Telegram: {title}")
        time.sleep(3)
    
    send_telegram("✅ <b>Done!</b> Check proposals above 👆")
    print("🎯 All done!")

if __name__ == "__main__":
    run()
