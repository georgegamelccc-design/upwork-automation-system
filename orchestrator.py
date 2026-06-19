import os, sys, time, subprocess, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/root/upwork-agent/.env")

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT  = os.getenv('TELEGRAM_CHAT_ID')
BASE_DIR = '/root/upwork-agent'
VENV_PY  = BASE_DIR + '/venv/bin/python3'

AGENTS = {
    'full_system':   {'script': 'full_system.py',   'process': None, 'restarts': 0},
    'message_agent': {'script': 'message_agent.py', 'process': None, 'restarts': 0},
}
job_bot_proc   = None
job_bot_active = False

def tg(msg, chat_id=None):
    try:
        requests.post('https://api.telegram.org/bot' + TG_TOKEN + '/sendMessage',
            json={'chat_id': chat_id or TG_CHAT, 'text': str(msg)[:4000], 'parse_mode': 'HTML'}, timeout=15)
    except Exception as e:
        print('[TG ERROR] ' + str(e))

def get_updates(offset):
    try:
        r = requests.get('https://api.telegram.org/bot' + TG_TOKEN + '/getUpdates',
            params={'offset': offset, 'timeout': 5}, timeout=10)
        return r.json().get('result', [])
    except:
        return []

def delete_webhook():
    try:
        requests.get('https://api.telegram.org/bot' + TG_TOKEN + '/deleteWebhook', timeout=10)
    except:
        pass

def start_agent(name):
    a = AGENTS[name]
    sp = BASE_DIR + '/' + a['script']
    if not os.path.exists(sp):
        print('[SKIP] ' + name)
        return
    proc = subprocess.Popen([VENV_PY, '-u', sp], cwd=BASE_DIR,
        stdout=open(BASE_DIR + '/' + name + '.log', 'a'), stderr=subprocess.STDOUT)
    a['process'] = proc
    print('[START] ' + name + ' PID=' + str(proc.pid))

def stop_agent(name):
    a = AGENTS[name]
    if a['process'] and a['process'].poll() is None:
        a['process'].terminate()
        a['process'].wait()
    a['process'] = None

def restart_agent(name):
    stop_agent(name)
    time.sleep(2)
    start_agent(name)
    AGENTS[name]['restarts'] += 1

def watchdog():
    for name, a in AGENTS.items():
        p = a['process']
        if p is None or p.poll() is not None:
            tg('<b>' + name + '</b> down - restarting...')
            restart_agent(name)
            tg('<b>' + name + '</b> restarted #' + str(a['restarts']))

def status_report():
    lines = ['<b>Orchestrator v2</b>']
    for name, a in AGENTS.items():
        p = a['process']
        if p and p.poll() is None:
            lines.append('UP: <b>' + name + '</b> PID=' + str(p.pid))
        else:
            lines.append('DOWN: <b>' + name + '</b>')
    global job_bot_proc, job_bot_active
    if job_bot_active and job_bot_proc and job_bot_proc.poll() is None:
        lines.append('UP: <b>job_bot</b> PID=' + str(job_bot_proc.pid))
    else:
        lines.append('STANDBY: <b>job_bot</b> - use /jobbot')
    lines.append(datetime.now().strftime('%H:%M:%S'))
    return chr(10).join(lines)

def start_job_bot():
    global job_bot_proc, job_bot_active
    sp = BASE_DIR + '/job_bot.py'
    if not os.path.exists(sp):
        tg('job_bot.py not found')
        return
    if job_bot_active and job_bot_proc and job_bot_proc.poll() is None:
        tg('job_bot already running!')
        return
    job_bot_proc = subprocess.Popen([VENV_PY, '-u', sp], cwd=BASE_DIR,
        stdout=open(BASE_DIR + '/job_bot.log', 'a'), stderr=subprocess.STDOUT)
    job_bot_active = True
    tg('job_bot started PID=' + str(job_bot_proc.pid) + chr(10) + 'ابعت رابط job او وصفه.')

def stop_job_bot():
    global job_bot_proc, job_bot_active
    if job_bot_proc and job_bot_proc.poll() is None:
        job_bot_proc.terminate()
        job_bot_proc.wait()
        tg('job_bot stopped.')
    job_bot_proc = None
    job_bot_active = False

def handle_command(text, chat_id):
    parts = text.strip().split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    if cmd == '/status':
        tg(status_report(), chat_id)
    elif cmd == '/help':
        tg('/status /restart_all /restart [name] /stop [name] /start [name] /jobbot /stopjobbot /agents /help', chat_id)
    elif cmd == '/restart_all':
        for name in AGENTS: restart_agent(name)
        tg('All restarted!', chat_id)
    elif cmd == '/restart':
        name = args[0] if args else ''
        if name in AGENTS:
            restart_agent(name)
            tg(name + ' restarted!', chat_id)
        else:
            tg('Unknown: ' + name, chat_id)
    elif cmd == '/stop':
        name = args[0] if args else ''
        if name in AGENTS:
            stop_agent(name)
            tg(name + ' stopped.', chat_id)
        else:
            tg('Unknown: ' + name, chat_id)
    elif cmd == '/start':
        name = args[0] if args else ''
        if name in AGENTS:
            start_agent(name)
            tg(name + ' started!', chat_id)
        else:
            tg('Unknown: ' + name, chat_id)
    elif cmd == '/jobbot':
        start_job_bot()
    elif cmd == '/stopjobbot':
        stop_job_bot()
    elif cmd == '/agents':
        tg('full_system | message_agent | job_bot (on-demand)', chat_id)
    else:
        tg('Unknown cmd. Use /help', chat_id)

def main():
    print('ORCHESTRATOR v2 Starting...')
    delete_webhook()
    for name in AGENTS:
        start_agent(name)
        time.sleep(2)
    tg('Orchestrator v2 LIVE' + chr(10) + 'full_system: UP' + chr(10) + 'message_agent: UP' + chr(10) + 'job_bot: STANDBY' + chr(10) + '/jobbot = manual proposals' + chr(10) + '/help = commands')
    offset = 0
    wd_timer = time.time()
    while True:
        try:
            updates = get_updates(offset)
            for u in updates:
                offset = u['update_id'] + 1
                msg = u.get('message', {})
                text = msg.get('text', '').strip()
                chat_id = str(msg.get('chat', {}).get('id', ''))
                if chat_id != TG_CHAT:
                    continue
                if text.startswith('/'):
                    handle_command(text, chat_id)
            if time.time() - wd_timer > 60:
                watchdog()
                wd_timer = time.time()
            time.sleep(3)
        except KeyboardInterrupt:
            tg('Orchestrator stopped.')
            for name in AGENTS: stop_agent(name)
            stop_job_bot()
            sys.exit(0)
        except Exception as e:
            print('[ERROR] ' + str(e))
            time.sleep(10)

if __name__ == '__main__':
    main()