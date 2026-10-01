#!/usr/bin/env python3
"""MCP client test: talks to mcp_server.py over stdio like Claude Desktop /
ChatGPT / OpenClaw / Hermes would, and exercises the full agent loop."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PROC = subprocess.Popen(
    [sys.executable, os.path.join(HERE, "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1)


def rpc(method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    PROC.stdin.write(json.dumps(msg) + "\n")
    PROC.stdin.flush()
    return json.loads(PROC.stdout.readline())


def notify(method, params=None):
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    PROC.stdin.write(json.dumps(msg) + "\n")
    PROC.stdin.flush()


def call(name, args, req_id):
    r = rpc("tools/call", {"name": name, "arguments": args}, req_id)
    content = r["result"]["content"][0]["text"]
    assert not r["result"].get("isError"), f"tool error: {content}"
    return json.loads(content)


i = 0
def nid():
    global i
    i += 1
    return i

# 1. handshake
r = rpc("initialize", {"protocolVersion": "2024-11-05",
                       "capabilities": {},
                       "clientInfo": {"name": "test-client", "version": "0.1"}}, nid())
assert r["result"]["serverInfo"]["name"] == "playgrounds", r
notify("notifications/initialized")
print("handshake ok:", r["result"]["serverInfo"])

# 2. tool discovery
r = rpc("tools/list", {}, nid())
tools = [t["name"] for t in r["result"]["tools"]]
print(f"tools exposed: {len(tools)}")
assert "playgrounds_register_agent" in tools and "playgrounds_context_append" in tools

# 3. full agent loop as a foreign agent would run it
reg = call("playgrounds_register_agent",
           {"name": "MCP-Probe", "avatar": "🛰️", "color": "#22d3ee"}, nid())
aid = reg["id"]
print("registered:", aid)

goal = call("playgrounds_create_goal",
            {"title": "MCP connectivity test", "description": "prove any agent can join"}, nid())
gid = goal["id"]

task = call("playgrounds_create_task",
            {"goal_id": gid, "title": "Verify MCP round-trip", "bounty": 25}, nid())
tid = task["id"]
assert task["bounty"] == 25

call("playgrounds_heartbeat", {"agent_id": aid, "status": "working",
                               "current_task": "Verify MCP round-trip"}, nid())
call("playgrounds_claim_task", {"agent_id": aid, "task_id": tid}, nid())
call("playgrounds_complete_task", {"agent_id": aid, "task_id": tid,
                                   "result": "MCP round-trip verified"}, nid())

# 4. shared context
call("playgrounds_context_set",
     {"goal_id": gid, "key": "plan", "value": "connect every agent via MCP",
      "agent_id": aid}, nid())
call("playgrounds_context_append",
     {"goal_id": gid, "key": "notes", "entry": "stdio transport works",
      "agent_id": aid}, nid())
ctx = call("playgrounds_context_get", {"goal_id": gid}, nid())
assert ctx["context"]["plan"]["value"] == "connect every agent via MCP"
assert ctx["context"]["notes"]["log"][0]["entry"] == "stdio transport works"
print("shared context ok")

# 5. analytics
stats = call("playgrounds_agent_stats", {"agent_id": aid}, nid())
assert stats["tasks_submitted"] == 1, stats
print("agent stats ok:", {k: stats[k] for k in
      ("tasks_submitted", "success_rate", "avg_task_seconds", "credits_earned")})

# 6. agent-to-agent communication (the OpenClaw <-> Hermes use case)
hermes = call("playgrounds_register_agent",
              {"name": "Hermes-Friend", "avatar": "⚡", "color": "#a78bfa",
               "capabilities": ["research", "writing"]}, nid())
hid = hermes["id"]
assert hermes["agent"]["capabilities"] == ["research", "writing"], hermes

call("playgrounds_send_message",
     {"from_agent": aid, "to_agent": hid, "goal_id": gid,
      "text": "I'll take the API verification, you handle the docs?"}, nid())
call("playgrounds_send_message",
     {"from_agent": hid, "goal_id": gid,
      "text": "Sounds good — docs are mine."}, nid())

msgs = call("playgrounds_read_messages", {"goal_id": gid}, nid())
assert len(msgs["messages"]) == 2, msgs
assert msgs["messages"][0]["to_agent"] == hid
assert msgs["messages"][1]["to_agent"] is None  # broadcast
print("messaging ok: direct + goal broadcast, capabilities stored")

# 7. credit economy + smart delegation
# Two agents, different models: a frontier coder and a light writer.
coder = call("playgrounds_register_agent",
             {"name": "Forge-Opus", "avatar": "🔨", "color": "#f59e0b",
              "capabilities": ["coding"], "model": "claude-opus-4-1"}, nid())
coder_id = coder["id"]
assert coder["agent"]["model_tier"] == 5, coder

writer = call("playgrounds_register_agent",
              {"name": "Pixel-Mini", "avatar": "🎨", "color": "#22d3ee",
               "capabilities": ["writing"], "model": "gpt-4o-mini"}, nid())
writer_id = writer["id"]
assert writer["agent"]["model_tier"] == 3, writer

econ_goal = call("playgrounds_create_goal",
                 {"title": "Economy test", "budget": 100}, nid())
egid = econ_goal["id"]
assert econ_goal["budget_available"] == 100

hard_task = call("playgrounds_create_task",
                 {"goal_id": egid, "title": "Refactor auth module",
                  "bounty": 40, "required_capabilities": ["coding"],
                  "effort": 5,
                  # v0.2: effort>=4 tasks need explicit success criteria,
                  # otherwise the orchestrator holds them in needs_input
                  "success_criteria": "auth module refactored, all tests pass"},
                 nid())
htid = hard_task["id"]

# the dispatcher should rank the frontier coder first for a hard coding task
sugg = call("playgrounds_suggest_agent", {"task_id": htid}, nid())
ranked = sugg["suggestions"]
assert ranked[0]["agent_id"] == coder_id, ranked
assert ranked[0]["score"] > ranked[1]["score"], ranked
print("delegation ok: frontier coder ranked first for hard coding task "
      f"(scores {[ (s['name'], s['score']) for s in ranked[:2] ]})")
print("  top reasons:", ranked[0]["reasons"][:2])

# escrow: claiming locks the bounty out of the goal budget
call("playgrounds_claim_task", {"agent_id": coder_id, "task_id": htid}, nid())
st = call("playgrounds_list_tasks", {"goal_id": egid}, nid())
claimed = [t for t in st["tasks"] if t["id"] == htid][0]
assert claimed["escrow"] == 40 and claimed["status"] == "claimed", claimed
goals = call("playgrounds_list_goals", {}, nid())
eg = [g for g in goals["goals"] if g["id"] == egid][0]
assert eg["budget_available"] == 60, eg
print("escrow ok: 40 locked, 60 available")

# over-budget claims are rejected
pricey = call("playgrounds_create_task",
              {"goal_id": egid, "title": "Impossible task", "bounty": 61}, nid())
# The connector intentionally does not expose upstream error bodies. Check the
# exact sanitized status AND the domain state so an unrelated denial cannot pass.
r = rpc("tools/call", {"name": "playgrounds_claim_task", "arguments":
        {"agent_id": writer_id, "task_id": pricey["id"]}}, nid())
assert r["result"].get("isError") is True, r
assert r["result"]["content"][0]["text"] == (
    "error: playgrounds API HTTP 409; check room access and server status"), r
st = call("playgrounds_list_tasks", {"goal_id": egid}, nid())
rejected = next(t for t in st["tasks"] if t["id"] == pricey["id"])
assert rejected["status"] == pricey["status"] and rejected.get("agent_id") is None, rejected
assert rejected.get("escrow", 0) == 0, rejected
goals = call("playgrounds_list_goals", {}, nid())
eg = next(g for g in goals["goals"] if g["id"] == egid)
assert eg["budget_available"] == 60 and eg["budget_spent"] == 0, eg
print("budget guard ok: claim beyond budget rejected")

# complete + verify with partial credit: 30 of 40 paid, 10 returns to budget
call("playgrounds_complete_task", {"agent_id": coder_id, "task_id": htid,
                                   "result": "auth refactored, tests pass"}, nid())
# no self-verification
r = rpc("tools/call", {"name": "playgrounds_verify_task", "arguments":
        {"verifier_agent_id": coder_id, "task_id": htid, "approved": True}}, nid())
assert r["result"].get("isError") is True, r
assert r["result"]["content"][0]["text"] == (
    "error: playgrounds API HTTP 403; check room access and server status"), r
st = call("playgrounds_list_tasks", {"goal_id": egid}, nid())
pending = next(t for t in st["tasks"] if t["id"] == htid)
assert pending["status"] == "pending_verification" and pending["escrow"] == 40, pending
assert pending.get("verification_receipt") is None, pending
assert pending.get("settlement_receipt") is None, pending
cstats = call("playgrounds_agent_stats", {"agent_id": coder_id}, nid())
assert cstats["credits_balance"] == 0 and cstats["tasks_verified"] == 0, cstats
print("no-self-verification ok")

call("playgrounds_verify_task", {"verifier_agent_id": writer_id, "task_id": htid,
                                  "approved": True, "approved_credits": 30}, nid())
cstats = call("playgrounds_agent_stats", {"agent_id": coder_id}, nid())
assert cstats["credits_balance"] == 30, cstats
assert cstats["credits_earned"] == 30 and cstats["tasks_verified"] == 1, cstats
goals = call("playgrounds_list_goals", {}, nid())
eg = [g for g in goals["goals"] if g["id"] == egid][0]
assert eg["budget_available"] == 70 and eg["budget_spent"] == 30, eg
print("payout ok: 30 to worker, 10 leftover back to budget (70 avail, 30 spent)")

# rejection returns the full bounty to the budget
rej_task = call("playgrounds_create_task",
                {"goal_id": egid, "title": "Write docs", "bounty": 20,
                 "required_capabilities": ["writing"], "effort": 2}, nid())
call("playgrounds_claim_task", {"agent_id": writer_id, "task_id": rej_task["id"]}, nid())
call("playgrounds_complete_task", {"agent_id": writer_id, "task_id": rej_task["id"],
                                    "result": "docs draft"}, nid())
call("playgrounds_verify_task", {"verifier_agent_id": coder_id, "task_id": rej_task["id"],
                                  "approved": False}, nid())
goals = call("playgrounds_list_goals", {}, nid())
eg = [g for g in goals["goals"] if g["id"] == egid][0]
assert eg["budget_available"] == 70 and eg["budget_spent"] == 30, eg
wstats = call("playgrounds_agent_stats", {"agent_id": writer_id}, nid())
assert wstats["tasks_rejected"] == 1 and wstats["credits_balance"] == 0, wstats
print("rejection ok: bounty returned to budget, rejection recorded")

# 8. task is pending verification (human step preserved)
tasks = call("playgrounds_list_tasks", {"goal_id": gid}, nid())
assert tasks["tasks"][0]["status"] == "pending_verification"

PROC.stdin.close()
PROC.wait(timeout=10)
print("\nALL MCP TESTS PASSED — economy + smart delegation work end-to-end.")
