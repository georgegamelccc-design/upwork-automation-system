import os, requests
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv("/root/upwork-agent/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

user_state = {}

def send(chat_id, msg):
    requests.post("https://api.telegram.org/bot"+TG_TOKEN+"/sendMessage",
        json={"chat_id":chat_id,"text":str(msg)[:4000]}, timeout=10)

def generate_full_proposal(job_text):
    prompt = """You are George Gamel, an expert n8n & AI automation freelancer.
A client posted this job: """ + job_text + """

Generate a complete proposal package with these EXACT sections separated by '---':

SECTION 1 - COVER LETTER:
Write a personalized 130 word cover letter.
Start with: Hi,
- Hook about their specific problem
- Mention PropFlow project: https://github.com/georgegamelr-spec/propflow-real-estate-crm
- Show understanding of their needs
- End EXACTLY with:
Best regards,
George Gamel
n8n & AI Automation Expert

---

SECTION 2 - WORKFLOW EXPERIENCE:
Answer: Briefly describe an n8n workflow you built that used APIs, webhooks, CRM updates, and error handling. What made it reliable?
Write 150 words specific to their project type.

---

SECTION 3 - MILESTONES:
Answer: How would you structure this build into milestones, and what would you leave out to keep scope realistic?
Create 2 milestones with descriptions, timeline, and budget split (50/50).
Mention what to leave out for future phases.

---

SECTION 4 - REQUIREMENTS:
Answer: What information would you need before starting?
List 5 specific questions relevant to their exact project.

RULES:
- NEVER use brackets or placeholders
- Be specific to their project
- Sound like an experienced expert
- No generic answers"""

    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}]
    )
    return r.choices[0].message.content

def process_update(update):
    msg = update.get("message",{})
    text = msg.get("text","").strip()
    chat_id = str(msg.get("chat",{}).get("id",""))
    if not text or not chat_id:
        return

    state = user_state.get(chat_id, {})

    if text == "/start":
        send(chat_id, "مرحباً George!\n\nابعتلي:\n- رابط الـ job\n- أو وصف المشروع مباشرة\n\nوأنا هجهزلك:\n✅ Cover Letter\n✅ إجابة أسئلة الـ job\n✅ Milestones\n✅ Requirements")
        user_state[chat_id] = {}

    elif state.get("waiting") == "desc":
        job_text = text
        send(chat_id, "جاري توليد الـ proposal الكامل...")
        result = generate_full_proposal(job_text)
        
        parts = result.split("---")
        labels = ["📝 COVER LETTER", "⚙️ WORKFLOW EXPERIENCE", "🎯 MILESTONES", "❓ REQUIREMENTS"]
        
        for i, part in enumerate(parts):
            if part.strip():
                label = labels[i] if i < len(labels) else "📌 SECTION " + str(i+1)
                send(chat_id, label + "\n\n" + part.strip())
        
        user_state[chat_id] = {}

    elif "http" in text:
        if "upwork.com" in text or "freelancer.com" in text:
            if "freelancer.com" in text:
                send(chat_id, "جاري قراءة الـ job...")
                try:
                    h = {"User-Agent":"Mozilla/5.0"}
                    r = requests.get(text, headers=h, timeout=15)
                    soup = BeautifulSoup(r.text,"lxml")
                    title = soup.find("h1")
                    desc = soup.find("p")
                    job_text = (title.text.strip() if title else "") + " " + (desc.text.strip()[:500] if desc else "")
                    if len(job_text) > 20:
                        send(chat_id, "جاري توليد الـ proposal الكامل...")
                        result = generate_full_proposal(job_text)
                        parts = result.split("---")
                        labels = ["📝 COVER LETTER", "⚙️ WORKFLOW EXPERIENCE", "🎯 MILESTONES", "❓ REQUIREMENTS"]
                        for i, part in enumerate(parts):
                            if part.strip():
                                label = labels[i] if i < len(labels) else "📌 SECTION " + str(i+1)
                                send(chat_id, label + "\n\n" + part.strip())
                        return
                except:
                    pass
            
            user_state[chat_id] = {"waiting": "desc"}
            send(chat_id, "ابعتلي وصف الـ job (انسخه من الصفحة):")
        else:
            user_state[chat_id] = {"waiting": "desc"}
            send(chat_id, "ابعتلي وصف الـ job:")

    else:
        user_state[chat_id] = {"waiting": "desc"}
        send(chat_id, "جاري توليد الـ proposal الكامل...")
        result = generate_full_proposal(text)
        parts = result.split("---")
        labels = ["📝 COVER LETTER", "⚙️ WORKFLOW EXPERIENCE", "🎯 MILESTONES", "❓ REQUIREMENTS"]
        for i, part in enumerate(parts):
            if part.strip():
                label = labels[i] if i < len(labels) else "📌 SECTION " + str(i+1)
                send(chat_id, label + "\n\n" + part.strip())
        user_state[chat_id] = {}

print("Bot starting...")
offset = 0
while True:
    try:
        r = requests.get("https://api.telegram.org/bot"+TG_TOKEN+"/getUpdates",
            params={"offset":offset,"timeout":30}, timeout=35)
        updates = r.json().get("result",[])
        for update in updates:
            offset = update["update_id"] + 1
            process_update(update)
    except Exception as e:
        print("Error: "+str(e))
