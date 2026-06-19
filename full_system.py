import os, requests, json, time, sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("/root/upwork-agent/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
FL_TOKEN = os.getenv("FREELANCER_ACCESS_TOKEN")
BIDDER_ID = 92853789

MY_SKILL_IDS = {9,13,31,116,500,607,613,759,913,979,1002,1031,1093,1977,2164,2165,2719,2791,2944,3112}

def tg(msg):
    try:
        requests.post("https://api.telegram.org/bot"+TG_TOKEN+"/sendMessage",
            json={"chat_id":TG_CHAT,"text":str(msg)[:4000]}, timeout=15)
    except Exception as e:
        print("TG Error: "+str(e))

def get_jobs():
    h = {"Freelancer-OAuth-V1": FL_TOKEN}
    jobs = []
    for offset in [0,50,100,150]:
        try:
            r = requests.get(
                "https://www.freelancer.com/api/projects/0.1/projects/active/",
                headers=h,
                params={"limit":50,"offset":offset,"job_details":True,"full_description":True,"jobs[]":list(MY_SKILL_IDS)},
                timeout=30)
            if r.status_code == 200:
                fetched = r.json().get("result",{}).get("projects",[])
                jobs.extend(fetched)
                print(f"Offset {offset}: got {len(fetched)} jobs")
            else:
                print(f"Offset {offset} error: {r.status_code} {r.text[:100]}")
            time.sleep(1)
        except Exception as e:
            print("get_jobs error: "+str(e))
    return jobs

def score(title, desc, job_skills):
    text = (title+" "+desc).lower()
    skill_match = len(MY_SKILL_IDS.intersection(set(job_skills)))
    s = skill_match * 20
    core = ["n8n","make.com","zapier","ai automation","workflow automation","automate","openai","chatbot","ai agent","llm","zoho","crm automation","python automation","api integration","automation"]
    sec  = ["api","workflow","automation","bot","ai","integration","webhook","python","gpt","react","node","javascript"]
    exc  = ["video edit","graphic design","logo","seo writing","content writing","translation","legal","photo","music","3d model","animation","data entry","sales lead","lead generator","outside sales"]
    for k in core:
        if k in text: s += 20
    for k in sec:
        if k in text: s += 8
    for k in exc:
        if k in text: s -= 40
    return max(0, min(s, 100))

def get_client_name(project_id):
    h = {"Freelancer-OAuth-V1": FL_TOKEN}
    try:
        r = requests.get("https://www.freelancer.com/api/projects/0.1/projects/"+str(project_id)+"/",
            headers=h, params={"user_details":True}, timeout=15)
        if r.status_code == 200:
            owner = r.json().get("result",{}).get("owner",{})
            name = owner.get("display_name","") or owner.get("username","")
            return name if name else "there"
    except: pass
    return "there"

def write_proposal(title, desc, budget, client_name="there"):
    prompt = (
        "Write a 130 word freelance proposal. Sign it as George Gamel, automation expert.\n"
        "RULES:\n- NEVER use placeholders\n- Start with: Hi "+client_name+",\n"
        "- Mention specific tech relevant to job\n"
        "- End with: Best regards,\nGeorge | n8n & AI Automation Expert\n\n"
        "Job: "+title+"\nDetails: "+desc[:300]+"\nBudget: $"+str(budget)
    )
    r = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}])
    return r.choices[0].message.content

def send_bid(pid, proposal, amount):
    h = {"Freelancer-OAuth-V1": FL_TOKEN, "Content-Type": "application/json"}
    d = {"project_id":int(pid),"bidder_id":BIDDER_ID,"amount":float(amount),"period":7,"milestone_percentage":50,"description":proposal}
    try:
        r = requests.post("https://www.freelancer.com/api/projects/0.1/bids/", headers=h, json=d, timeout=30)
        if r.status_code == 200:
            return True, str(r.json().get("result",{}).get("id",""))
        err = r.json().get("message","unknown")
        print(f"BID FAILED {pid}: {r.status_code} - {err}")
        return False, err[:100]
    except Exception as e:
        print(f"BID EXCEPTION {pid}: {e}")
        return False, str(e)

def get_threads():
    h = {"Freelancer-OAuth-V1": FL_TOKEN}
    try:
        r = requests.get("https://www.freelancer.com/api/messages/0.1/threads/", headers=h, params={"limit":20}, timeout=15)
        if r.status_code == 200:
            return r.json().get("result",{}).get("threads",[])
    except: pass
    return []

def get_msgs(thread_id):
    h = {"Freelancer-OAuth-V1": FL_TOKEN}
    try:
        r = requests.get("https://www.freelancer.com/api/messages/0.1/threads/"+str(thread_id)+"/",
            headers=h, params={"limit":10,"include_messages":True}, timeout=15)
        if r.status_code == 200:
            return r.json().get("result",{}).get("messages",[])
    except: pass
    return []

def send_msg(thread_id, message):
    h = {"Freelancer-OAuth-V1": FL_TOKEN, "Content-Type": "application/json"}
    try:
        r = requests.post("https://www.freelancer.com/api/messages/0.1/messages/",
            headers=h, json={"thread_id":thread_id,"message":message}, timeout=15)
        return r.status_code == 200
    except: return False

def handle_client(msg_text, project_title):
    prompt = ("Expert automation engineer. Project: "+project_title+" Client message: "+msg_text+
              " Return JSON: clarification_needed (bool), clarification_question (str), reply_to_client (str)")
    r = client.chat.completions.create(model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
    return json.loads(r.choices[0].message.content)

def check_messages(conn):
    print("Checking messages...")
    threads = get_threads()
    print("Threads: "+str(len(threads)))
    for thread in threads:
        t = thread.get("thread",{}) if "thread" in thread else thread
        thread_id = t.get("id") or thread.get("id")
        if not thread_id: continue
        context = thread.get("context",{})
        project_id = str(context.get("id",""))
        msgs = get_msgs(thread_id)
        for msg in msgs:
            msg_id = str(msg.get("id",""))
            from_user = msg.get("from_user",{})
            sender_id = from_user.get("id",0) if isinstance(from_user,dict) else 0
            msg_text = msg.get("message","")
            if sender_id != BIDDER_ID and msg_text:
                if not conn.execute("SELECT message_id FROM handled_messages WHERE message_id=?",(msg_id,)).fetchone():
                    row = conn.execute("SELECT title FROM jobs WHERE id=?",(project_id,)).fetchone()
                    title = row[0] if row else "Automation Project"
                    print("NEW MSG: "+msg_text[:80])
                    tg("NEW CLIENT MSG\nProject: "+title+"\nMessage: "+msg_text[:200])
                    try:
                        analysis = handle_client(msg_text, title)
                        if analysis.get("clarification_needed"):
                            q = analysis.get("clarification_question","Can you provide more details?")
                            send_msg(thread_id, q)
                            tg("CLARIFICATION SENT: "+q)
                        else:
                            reply = analysis.get("reply_to_client","")
                            if reply:
                                send_msg(thread_id, reply)
                                tg("REPLY SENT: "+reply[:200])
                    except Exception as e:
                        print("handle_client error: "+str(e))
                    conn.execute("INSERT OR IGNORE INTO handled_messages VALUES (?,?,?,?)",
                        (str(thread_id),msg_id,"handled",datetime.now().isoformat()))
                    conn.commit()

def check_payments(conn):
    print("Checking payments...")
    h = {"Freelancer-OAuth-V1": FL_TOKEN}
    try:
        r = requests.get("https://www.freelancer.com/api/projects/0.1/milestones/",
            headers=h, params={"bidders[]":BIDDER_ID,"limit":50}, timeout=15)
        if r.status_code != 200: return
        milestones = r.json().get("result",{}).get("milestones",{})
        if not milestones: return
        for mid, milestone in milestones.items():
            milestone_id = str(milestone.get("id",""))
            status = milestone.get("status","")
            amount = milestone.get("amount",0)
            project_id = str(milestone.get("project_id",""))
            key = "payment_"+milestone_id if status=="funded" else "released_"+milestone_id
            if status in ("funded","released"):
                if not conn.execute("SELECT message_id FROM handled_messages WHERE message_id=?",(key,)).fetchone():
                    row = conn.execute("SELECT title FROM jobs WHERE id=?",(project_id,)).fetchone()
                    title = row[0] if row else "Project"
                    if status == "funded":
                        tg("PAYMENT RECEIVED!\nProject: "+title+"\nAmount: $"+str(amount))
                    else:
                        tg("MONEY IN YOUR ACCOUNT!\nProject: "+title+"\nAmount: $"+str(amount))
                    conn.execute("INSERT OR IGNORE INTO handled_messages VALUES (?,?,?,?)",
                        (project_id,key,status,datetime.now().isoformat()))
                    conn.commit()
    except Exception as e:
        print("check_payments error: "+str(e))

def init_db():
    conn = sqlite3.connect("/root/upwork-agent/system.db")
    conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, title TEXT, url TEXT, status TEXT, proposal TEXT, score INTEGER, bid_id TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS handled_messages (thread_id TEXT, message_id TEXT PRIMARY KEY, status TEXT, created_at TEXT)")
    conn.commit()
    return conn

def run_cycle(conn):
    print(datetime.now().strftime("%H:%M:%S")+" - Cycle start")
    jobs = get_jobs()
    print("Jobs fetched: "+str(len(jobs)))
    scored = []
    for j in jobs:
        job_skill_ids = [sk.get("id",0) for sk in j.get("jobs",[])]
        s = score(j.get("title",""), j.get("description",""), job_skill_ids)
        scored.append((j,s))
    scored = [(j,s) for j,s in scored if s >= 25]
    scored.sort(key=lambda x: x[1], reverse=True)
    new = [(j,s) for j,s in scored if not conn.execute("SELECT id FROM jobs WHERE id=?",(str(j.get("id","")),)).fetchone()]
    print("New qualified: "+str(len(new)))
    if new: tg("Found "+str(len(new))+" new jobs - sending proposals")
    sent_count = 0
    for job,s in new[:5]:
        jid    = str(job.get("id",""))
        title  = job.get("title","")
        desc   = job.get("description","")
        bmin   = job.get("budget",{}).get("minimum",200)
        bmax   = job.get("budget",{}).get("maximum",1000)
        amount = max(int((bmin+bmax)/2), int(bmin*1.1), 50)
        if bmax > 2400: continue  # skip verified-only projects
        url    = "https://www.freelancer.com/projects/"+str(job.get("seo_url",jid))
        client_name  = get_client_name(jid)
        proposal     = write_proposal(title, desc, amount, client_name)
        sent, bid_id = send_bid(jid, proposal, amount)
        status = "sent" if sent else "drafted"
        conn.execute("INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,?,?,?)",
            (jid,title,url,status,proposal,s,bid_id,datetime.now().isoformat()))
        conn.commit()
        icon = "SENT" if sent else "DRAFT"
        tg(icon+" Score:"+str(s)+"/100\n"+title+"\n"+url+"\n\n"+proposal[:500])
        print(icon+": "+title[:60]+" | "+str(bid_id))
        if sent: sent_count += 1
        time.sleep(3)
    print(f"Sent: {sent_count}/{len(new[:5])}")
    check_payments(conn)
    check_messages(conn)

def main():
    print("System v2 Starting...")
    tg("FULL SYSTEM v2 LIVE - Skills-filtered bidding active!")
    conn = init_db()
    while True:
        try:
            run_cycle(conn)
        except Exception as e:
            print("Cycle Error: "+str(e))
            tg("ERROR: "+str(e))
        print("Sleeping 30 min...")
        time.sleep(1800)

if __name__ == "__main__":
    main()
