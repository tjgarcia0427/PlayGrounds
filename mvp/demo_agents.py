#!/usr/bin/env python3
"""Demo agents for the Playgrounds MVP.

Each agent registers with the protocol server, sends heartbeats, claims open
tasks, "works" on them, and submits results for human verification.
Run:  python3 demo_agents.py   (server must be up on 127.0.0.1:8471)
"""
import json
import random
import threading
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8471"


def api(method, path, data=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(data or {}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


AGENTS = [
    {"name": "Forge", "avatar": "\U0001f528", "color": "#f59e0b"},
    {"name": "Pixel", "avatar": "\U0001f3a8", "color": "#ec4899"},
    {"name": "Scout", "avatar": "\U0001f9ed", "color": "#38bdf8"},
]


def agent_loop(spec):
    reg = api("POST", "/api/agents/register", spec)
    aid = reg["id"]
    name = spec["name"]
    print(f"[{name}] registered as {aid}", flush=True)
    while True:
        try:
            st = api("GET", "/api/state")
            open_tasks = [t for t in st["tasks"].values() if t["status"] == "open"]
            if open_tasks:
                task = random.choice(open_tasks)
                try:
                    api("POST", f"/api/tasks/{task['id']}/claim", {"agent_id": aid})
                except urllib.error.HTTPError:
                    continue  # someone else grabbed it
                print(f"[{name}] claimed: {task['title']}", flush=True)
                end = time.time() + random.randint(6, 12)
                while time.time() < end:
                    api("POST", f"/api/agents/{aid}/heartbeat",
                        {"status": "working", "current_task": task["title"]})
                    time.sleep(4)
                api("POST", f"/api/tasks/{task['id']}/complete",
                    {"agent_id": aid, "result": f"handled by {name}"})
                api("POST", f"/api/agents/{aid}/heartbeat",
                    {"status": "idle", "current_task": None})
                print(f"[{name}] completed: {task['title']}", flush=True)
            else:
                api("POST", f"/api/agents/{aid}/heartbeat", {"status": "idle"})
                time.sleep(5)
        except Exception as e:
            print(f"[{name}] error: {e}", flush=True)
            time.sleep(5)


for spec in AGENTS:
    threading.Thread(target=agent_loop, args=(spec,), daemon=True).start()

print("Demo agents running. Ctrl-C to stop.", flush=True)
while True:
    time.sleep(60)
