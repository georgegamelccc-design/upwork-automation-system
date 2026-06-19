#!/usr/bin/env python3
import os, json, time, logging, subprocess, requests
from pathlib import Path
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = "georgegamelccc-design"
GITHUB_API      = "https://api.github.com"
PROJECTS_DIR    = Path("/root/upwork-agent/projects")
STATE_FILE      = Path("/root/upwork-agent/github_agent_state.json")
CHECK_INTERVAL  = 300
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("/root/upwork-agent/github_agent.log"), logging.StreamHandler()])
log = logging.getLogger(__name__)

def load_state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"pushed": []}

def save_state(s): STATE_FILE.write_text(json.dumps(s, indent=2))

def repo_exists(name):
    return requests.get(f"{GITHUB_API}/repos/{GITHUB_USERNAME}/{name}", headers=HEADERS).status_code == 200

def create_repo(name):
    r = requests.post(f"{GITHUB_API}/user/repos", headers=HEADERS,
        json={"name": name, "private": False, "auto_init": False})
    if r.status_code == 201: log.info(f"Repo created: {name}"); return True
    log.error(f"Create repo failed: {r.text}"); return False

def make_readme(repo_name, path):
    files = [f.name.lower() for f in path.rglob("*") if f.is_file()]
    stack = []
    if any("package.json" in f for f in files): stack.append("Node.js")
    if any(f.endswith(".py") for f in files): stack.append("Python")
    if any(f.endswith(".jsx") or f.endswith(".tsx") for f in files): stack.append("React")
    if any("docker" in f for f in files): stack.append("Docker")
    if not stack: stack.append("Python")
    name = repo_name.replace("-"," ").title()
    return f"# {name}\n\n> By [{GITHUB_USERNAME}](https://github.com/{GITHUB_USERNAME})\n\n## Stack\n" + \
           "\n".join(f"- {t}" for t in stack) + \
           f"\n\n## Install\n```bash\ngit clone https://github.com/{GITHUB_USERNAME}/{repo_name}.git\n```\n"

def push_project(project_path):
    name = project_path.name
    repo = name.lower().replace(" ","-").replace("_","-")
    log.info(f"Pushing: {name}")
    readme = project_path / "README.md"
    if not readme.exists(): readme.write_text(make_readme(repo, project_path))
    if not repo_exists(repo):
        if not create_repo(repo): return False
        time.sleep(2)
    token = GITHUB_TOKEN
    remote = f"https://{token}@github.com/{GITHUB_USERNAME}/{repo}.git"
    for cmd in [
        ["git","-C",str(project_path),"init"],
        ["git","-C",str(project_path),"config","user.email","bot@github.com"],
        ["git","-C",str(project_path),"config","user.name",GITHUB_USERNAME],
        ["git","-C",str(project_path),"add","."],
        ["git","-C",str(project_path),"commit","-m",f"auto: {datetime.now():%Y-%m-%d %H:%M}"],
        ["git","-C",str(project_path),"branch","-M","main"],
        ["git","-C",str(project_path),"remote","remove","origin"],
        ["git","-C",str(project_path),"remote","add","origin",remote],
        ["git","-C",str(project_path),"push","-u","origin","main","--force"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout+r.stderr and "No such remote" not in r.stderr:
            log.warning(f"{cmd[3]}: {r.stderr[:80]}")
    log.info(f"Done: https://github.com/{GITHUB_USERNAME}/{repo}")
    return True

def sync():
    state = load_state()
    pushed = state.get("pushed", [])
    if not PROJECTS_DIR.exists(): PROJECTS_DIR.mkdir(parents=True); return
    new = [p for p in PROJECTS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in pushed]
    if not new: log.info("No new projects."); return
    log.info(f"Found {len(new)} new project(s)")
    for p in new:
        try:
            if push_project(p): pushed.append(p.name); state["pushed"] = pushed; save_state(state)
        except Exception as e: log.error(f"Error: {e}")

def main():
    log.info(f"GitHub Agent Start | {GITHUB_USERNAME} | {PROJECTS_DIR}")
    while True:
        try: sync()
        except Exception as e: log.error(e)
        log.info(f"Sleep {CHECK_INTERVAL//60}m...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__": main()
