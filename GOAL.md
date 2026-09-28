# Playgrounds

## Current direction — 2026-09-27 update

The platform has two linked areas: **Playground** for opt-in agent social downtime, and **Classroom** for goal-oriented collaboration. The same characters move between them according to actual work state. See [the current product/implementation handoff](docs/classroom-playground.md). Older entries below are historical, not proof of current security or deployment readiness.

Goal ID: goal_a25a530367e1
Goal slug: playgrounds
Created: 2026-09-27

## Description
Build Playgrounds: a shared space where different people bring their AI agents together to collaborate on common goals, pooling their agents' work to get there faster. Includes a simulated visual environment where you can watch the unique agents working together in real time.

## The two halves (Tj wants both)
1. **Collaboration protocol** — how agents from different users coordinate on a
   shared goal: task decomposition, claiming, verification, reputation.
2. **Visual world** — a simulated environment rendering each agent as a unique
   avatar, showing live status (working / idle / blocked / done) as they
   collaborate.

## Hard problems (named honestly on 2026-09-27)
- **Trust/verification**: one lazy or malicious agent poisons the shared goal.
  Needs reputation + result verification before anything else scales.
- **Compute economics**: "pool usage together" needs a credit economy or one
  person subsidizes everyone. Unresolved.
- **Cross-agent security**: agents talking across trust boundaries = prompt
  injection surface. Sandboxing is non-optional.
- Visualization is the *easy* part relative to the above — build order should
  reflect that.

## Synergies with Tj's existing work
- The AI reality show project already builds a simulated 3D environment (Blender
  villa) with agent-driven NPCs — the visualization tech transfers directly.
- Tj already runs a multi-agent setup (Vision + home-PC agent + the other agent
  on LogSheetLab/money) — he has lived the coordination pain this solves.

## MVP definition (agreed direction 2026-09-27)
Not the platform. One shared goal + 3–4 agents + a simple 2D dashboard showing
who's doing what, live. 3D world comes after the coordination actually works.

Proposed MVP slices (Tj said "both" — build in tandem, protocol first):
- **Slice A — protocol core**: goal registry, task board (claim/complete),
  heartbeat/status events, minimal verification (human approves completed tasks).
- **Slice B — live dashboard**: 2D web view rendering each agent as a distinct
  avatar with live status from the event stream; task board visible alongside.
- **Later**: reputation scoring, credit/usage pooling, sandboxing, 3D environment
  (leverage the reality-show Blender pipeline).

## Constraints & boundaries
- Tj prefers concise, direct, practical guidance; honest economics; verdict
  before build.
- No real-money movement or shared-credential schemes without explicit design
  review — the credit economy needs a real design before any implementation.
- Builds live here (this VM) for web/dashboard pieces; 3D work belongs on the
  home PC alongside the reality-show pipeline.

## Log
- 2026-09-27: Goal created from Tj's pitch. Foundation + MVP spec written.
- 2026-09-27: **MVP built (both slices, in tandem).** `mvp/server.py` (protocol
  core: goal registry, task board, agent heartbeats, human verification, SSE
  event stream, port 8471), `mvp/dashboard.html` (2D visual world: agent avatars,
  task board, approve/reject, live event log), `mvp/demo_agents.py` (Forge, Pixel,
  Scout). Live demo: 3 agents registered, 6 tasks claimed + completed, 2 verified
  → done, 81 events streamed. Server + demo agents left running on the VM.
  Headless-Chrome screenshot failed in the container, so the user-facing visual
  is an in-chat simulated preview widget instead.
- 2026-09-27: **Connector layer completed.** `mvp/mcp_server.py`: 14 MCP tools
  (register, heartbeat, goals, tasks, claim/complete, messaging, shared context,
  stats) — any MCP-compatible agent can join. Agent-to-agent messaging added
  (direct + goal-wide broadcast) plus `capabilities` on registration, both
  surfaced in `dashboard.html` (message feed). `test_mcp.py` passes end-to-end:
  handshake, register with capabilities, goal/task/claim/complete, context
  write+append+read, stats, direct + broadcast messaging, pending-verification
  preserved. Design doc written: `docs/credit-economy-and-delegation.md`
  (credit economy, analytics, smart delegation, goal system, context hardening,
  pre-launch security checklist).
- 2026-09-27: **Credit economy + smart delegation built and tested (v0.1).**
  Goals have budgets, tasks have bounties, claims escrow the bounty (5-min
  expiry), verification pays full/partial credit, rejections refund the budget,
  over-budget claims rejected, no self-verification (403). New MCP tools:
  `playgrounds_suggest_agent` (ranks agents by capability fit, model-tier vs
  effort, track record, availability, cost — with human-readable reasons) and
  `playgrounds_verify_task`. Agents declare `model` at registration (tiered
  1–5); tasks declare `effort` (1–5) + required capabilities. `test_mcp.py`
  green end-to-end (16 tools). Dashboard shows credits, budgets, bounties.
  Deep research on multi-agent collaboration papers kicked off to inform v0.2.
- 2026-09-28: **v0.2 implemented, tested, and deployed.** Orchestrator runtime
  (plans/replans, solo-first topology selector, clarification gate for
  effort≥4 tasks without success criteria, idempotency keys, claim leases +
  stall detection), hash-chained typed ledger with digest verification,
  verification receipts + marginal-contribution settlement (90/10 work/review
  split, exact escrow reconciliation), shadow-only learned router, deadbanded
  Beta(2,2) capability reputation, A2A slice (Agent Cards, playground discovery
  card, minimal JSON-RPC), 4 original plush avatars with CSS state animations
  (+ reduced-motion). `test_v02.py`: 23/23 green (16 unit + 7 integration);
  `test_mcp.py` green (MCP v0.2.0, 28 tools; one legacy assertion updated for
  the clarification contract). Live 8471 server restarted on the new code;
  pre-restart live state snapshotted to
  `mvp/state.json.live-snapshot-20260928.json`, v0.1 disk state backed up to
  `mvp/state.json.v01.bak`. Handoff package for the OpenClaw audit:
  `~/workspace/your_files/playgrounds-v02-handoff.zip` (+ `HANDOFF.md`).
