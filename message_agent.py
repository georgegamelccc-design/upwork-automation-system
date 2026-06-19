import os, requests, json, time, sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("/root/upwork-agent/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")
FL_TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
BIDDER_ID = 92853789

SYSTEM_PROMPT = """You are George Gamel's assistant on Freelancer.com. Reply to clients on his behalf.

GEORGE CAN DO: n8n automation, Make.com, Zapier, OpenAI/GPT-4o integration, AI chatbots, Python automation, REST API integration, WhatsApp/Telegram bots, CRM automation (Zoho/HubSpot), PostgreSQL/Supabase, React.js/Next.js, Node.js/Express, Docker, web scraping, lead generation automation, JavaScript/TypeScript, Linux server setup.

GEORGE CANNOT DO: Mobile apps (iOS/Android/Flutter), Blockchain/Web3/NFTs, Video editing, Graphic design, SEO writing, Translation, 3D modeling, Game development, ML model training, Hardware/IoT, SAP/Oracle ERP, Paid ads management.

PRICING: Small automation $150-400 | Medium project $400-1200 | Large project $1200-3000 | Hourly $35-55/hr
DELIVERY: Simple 2-5 days | Medium 1-2 weeks | Large 3-4 weeks

RULES:
1. NEVER promise things outside capabilities
2. If client asks for something George cannot do — decline politely and offer what he CAN do
3. Be confident about what George CAN deliver
4. 100-150 words max
5. End with a question or next step
6. Sign as: George | Automation & AI Expert
7. English only
8. NEVER use placeholders like [your name]
9. If completely outside capabilities — be honest and wish them luck

Return JSON only:
{"can_handle": true/false, "confidence": "high/medium/low", "reply": "message to send", "internal_note": "what this project needs"}"""

def tg(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TG_TOKEN+"/sendMessage",
            json={"chat_id":TG_CHAT,"text":str(msg)[:4000]}, timeout=15)
    except Exception as e:
        print("TG:"+str(e))

def get_threads():
    try:
        r = requests.get("https://www.freelancer.com/api/messages/0.1/threads/",
            headers={"Freelancer-OAuth-V1":FL_TOKEN}, params={"limit":30}, timeout=15)
        if r.status_code == 200:
            return r.json().get("result",{}).get("threads",[])
    except Exception as e:
        print("threads err:"+str(e))
    return []

def get_msgs(thread_id):
    try:
        r = requests.get("https://www.freelancer.com/api/messages/0.1/threads/"+str(thread_id)+"/",
            headers={"Freelancer-OAuth-V1":FL_TOKEN},
            params={"limit":20,"include_messages":True}, timeout=15)
        if r.status_code == 200:
            return r.json().get("result",{}).get("messages",[])
    except Exception as e:
        print("msgs err:"+str(e))
    return []

def send_msg(thread_id, message):
    try:
        r = requests.post("https://www.freelancer.com/api/messages/0.1/messages/",
            headers={"Freelancer-OAuth-V1":FL_TOKEN,"Content-Type":"application/json"},
            json={"thread_id":thread_id,"message":message}, timeout=15)
        return r.status_code == 200
    except Exception as e:
        print("send err:"+str(e))
        return False

def generate_reply(client_msg, project_title, history=""):
    ctx = ("\nPrevious:\n"+history+"\n") if history else ""
    prompt = "Project: "+project_title+ctx+"\nClient: "+client_msg
    try:
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],
            response_format={"type":"json_object"}, temperature=0.7)
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print("gpt err:"+str(e))
        return None

def init_db():
    conn = sqlite3.connect("/root/upwork-agent/messages.db")
    conn.execute("CREATE TABLE IF NOT EXISTS handled_msgs (message_id TEXT PRIMARY KEY, thread_id TEXT, project_title TEXT, client_msg TEXT, reply_sent TEXT, can_handle INTEGER, confidence TEXT, internal_note TEXT, created_at TEXT)")
    conn.commit()
    return conn

def run(conn):
    print(datetime.now().strftime("%H:%M:%S")+" - Checking messages...")
    threads = get_threads()
    print("Threads: "+str(len(threads)))
    replied = 0
    for thread in threads:
        t = thread.get("thread",{}) if "thread" in thread else thread
        thread_id = t.get("id") or thread.get("id")
        if not thread_id: continue
        ctx = thread.get("context",{})
        project_title = ctx.get("title","") or ctx.get("name","") or "Automation Project"
        msgs = get_msgs(thread_id)
        for msg in msgs:
            msg_id = str(msg.get("id",""))
            fu = msg.get("from_user",{})
            sender_id = fu.get("id",0) if isinstance(fu,dict) else 0
            msg_text = msg.get("message","").strip()
            if sender_id == BIDDER_ID or not msg_text: continue
            if conn.execute("SELECT message_id FROM handled_msgs WHERE message_id=?",(msg_id,)).fetchone(): continue
            print("\nNEW ["+project_title[:40]+"]: "+msg_text[:80])
            history = "\n".join([("George" if (m.get("from_user",{}).get("id",0) if isinstance(m.get("from_user",{}),dict) else 0)==BIDDER_ID else "Client")+": "+m.get("message","") for m in msgs if str(m.get("id",""))!=msg_id and m.get("message","")][-6:])
            result = generate_reply(msg_text, project_title, history)
            if not result: continue
            can_handle = result.get("can_handle",True)
            confidence = result.get("confidence","medium")
            reply = result.get("reply","")
            note = result.get("internal_note","")
            print("  "+str(can_handle)+" | "+confidence+" | "+note[:60])
            sent = send_msg(thread_id, reply) if reply else False
            tg(("✅" if sent else "❌")+" REPLY | "+("🟢" if can_handle else "🔴")+"\nProject: "+project_title[:50]+"\nClient: "+msg_text[:150]+"\n\nGeorge: "+reply[:250]+"\nNote: "+note[:80])
            conn.execute("INSERT OR IGNORE INTO handled_msgs VALUES (?,?,?,?,?,?,?,?,?)",
                (msg_id,str(thread_id),project_title,msg_text,reply if sent else "",int(can_handle),confidence,note,datetime.now().isoformat()))
            conn.commit()
            if sent: replied += 1
            time.sleep(2)
    print("Replied: "+str(replied))

def main():
    print("Message Agent Starting...")
    tg("💬 Message Agent LIVE")
    conn = init_db()
    while True:
        try:
            run(conn)
        except Exception as e:
            print("Error: "+str(e))
            tg("❌ Error: "+str(e))
        print("Sleeping 5 min...")
        time.sleep(300)

if __name__ == "__main__":
    main()
