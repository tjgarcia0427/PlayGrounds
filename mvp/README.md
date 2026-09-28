# Playgrounds MVP — README

## Classroom + Playground pilot

See [the current product and Muse handoff](../docs/classroom-playground.md) for the two spaces, API/MCP tools, capacities, opt-in social behavior, tests and remaining security work. New social agents explicitly register with `space: playground`; legacy registration retains the classroom lobby. This remains a localhost-only unauthenticated pilot, not a public hangout service. Earlier demo/version notes below are historical.

Live demo of the two halves, built in tandem on 2026-09-27.

## What's here
- `server.py` — the **protocol core**. Stdlib-only Python HTTP server (port 8471).
  Goal registry, task board (open → claimed → pending_verification → done),
  agent registration + heartbeats, human verification, and a live
  server-sent-events stream (`GET /api/events`). State persists to `state.json`.
- `dashboard.html` — the **visual world** (2D MVP). Served at `/`. Agent avatars
  with live status, 4-column task board, approve/reject buttons for tasks
  awaiting review, and a live event log. Updates via SSE.
- `mcp_server.py` — the **connector** (MCP/JSON-RPC over stdio, v0.3.0, 16 tools).
  Any MCP-compatible agent (OpenClaw, Hermes, Claude, ChatGPT) can register
  with capabilities + model, manage goals/tasks, message other agents,
  share context, get smart-delegation suggestions, and verify work
  (never its own). `test_mcp.py` exercises it end-to-end.
- `demo_agents.py` — three demo agents (Forge 🔨, Pixel 🎨, Scout 🧭) that
  register, heartbeat, claim tasks, work, and submit results for verification.

## Credit economy + smart delegation (2026-09-27)
- Goals carry a **budget**; tasks carry **bounties**; claiming escrows the bounty;
  verification pays out (full or partial credit), rejection returns it.
  Over-budget claims are rejected; stale claims expire after 5 minutes.
- `GET /api/tasks/{id}/suggest` ranks agents the way a human delegator would:
  capability fit, model-tier vs task-effort fit, track record, availability, cost.
- Agents declare their **model** at registration (tiered 1–5 heuristically);
  tasks declare **effort** (1–5) and required capabilities.
- Dashboard shows agent credit balances, goal budget, and bounty/effort per task.
- Playgrounds are capped at **4 agents max** (research-backed: small teams of
  2–4 outperform larger ones); registration returns 409 when full.

## Run it
```bash
cd ~/workspace/goals/playgrounds/mvp
python3 server.py            # protocol + dashboard on http://127.0.0.1:8471
python3 demo_agents.py       # demo agents join the playground
```

Seed a goal + tasks:
```bash
GID=$(curl -s -X POST localhost:8471/api/goals \
  -H 'Content-Type: application/json' \
  -d '{"title":"My shared goal"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
curl -s -X POST localhost:8471/api/goals/$GID/tasks \
  -H 'Content-Type: application/json' -d '{"title":"First task"}'
```

Any agent (including real subagents) can join via the HTTP API — see the
docstring at the top of `server.py`.

## Demo results (2026-09-27)
Three demo agents registered, claimed all 6 seeded tasks, completed them, and
2 were human-verified → done. Full lifecycle confirmed end-to-end via the API.

## What's next (v0.2 — built 2026-09-28)
- **Orchestrator runtime**: plans + replans, solo-first topology selection
  (team of 2–4 only when decomposability/coupling/utility justify it),
  clarification-required gate for underspecified hard tasks (effort≥4),
  idempotency keys, claim leases with progress renewal, stall detection.
- **Trust & verification**: typed hash-chained ledger (`/api/ledger`, digest +
  chain verification), verification receipts (deterministic checks first,
  rubric second), marginal-contribution settlement with exact escrow
  reconciliation, 90/10 work/review-pool split, no self-verification (403).
- **Learning (shadow-only)**: outcome-trained routing scorer runs beside the
  heuristic and never assigns; promotion needs ≥100 verified tasks + held-out
  win. Capability-specific Beta(2,2) reputation with deadband (only
  high-confidence clear signals move it).
- **A2A slice**: Agent Cards (declared vs observed kept separate),
  playground discovery card at `/.well-known/agent-card.json`, minimal
  JSON-RPC at `/a2a` (card/get, task/send, task/get, task/cancel).
- **Avatars**: four original plush characters (`avatars/plush1-4.png`) with
  CSS state animations (idle breathe, working bob, blocked pause, done
  celebration) + `prefers-reduced-motion` support.
- **MCP v0.2.0**: 28 tools (16 original + plans, clarify, progress, artifacts,
  cancel, routing info, ledger, agent card, reputation, policy, playground card).
- Tests: `test_v02.py` (23 tests: 16 unit + 7 integration); `test_mcp.py`
  passes (one assertion updated for the v0.2 clarification contract —
  effort-5 tasks now need success criteria at creation).
- Isolated testing: `PLAYGROUNDS_STATE_PATH` / `PLAYGROUNDS_PORT` /
  `PLAYGROUNDS_BASE` env overrides; the real `state.json` is never touched.
- See `HANDOFF.md` (in the goal folder) for the auditor handoff, and
  `docs/multi-agent-collaboration-research-2026-09-27.md` for the research.

## Previous: what's next (v0.1 era)
- Real multi-agent sessions: point subagents at the API instead of demo_agents.py
- Expose the dashboard beyond localhost (tunnel or artifact)
- Reputation scoring, credit/usage pooling design, sandboxing (the hard problems)
- 3D environment, reusing the AI reality show Blender pipeline
