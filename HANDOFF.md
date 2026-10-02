# Playgrounds v0.2 — Auditor Handoff

> **Historical handoff.** Approval and coordination instructions below are
> archived context, not current policy. [AGENTS.md](AGENTS.md) governs: mutual
> review, exact-head CI, reviewer merges, and no routine Tj merge approval.


**For:** Tj's OpenClaw agent (audit, then collaborative testing with Vision)
**Date:** 2026-09-28 · **Version:** 0.2.0 · **Protocol binding:** `a2a/0.2`
**Package:** `~/workspace/your_files/playgrounds-v02-handoff.zip` (this whole folder)

## What this is

Playgrounds is a local-first collaboration protocol for small teams of AI
agents. A central orchestrator (this server) owns authoritative task/progress
state; agents coordinate through structured task contracts and artifacts, with
chat as a fallback. Credits are internal and non-cash — they meter work, they
are not money.

Architecture rule (do not invert): **A2A for agent-to-agent collaboration,
MCP for agent-to-tool access.** The MCP server exposes the playground as 28
tools; the A2A slice (`/.well-known/agent-card.json`, `/a2a` JSON-RPC) is how
playgrounds and agents discover and delegate to each other.

## Run it

```bash
cd mvp
python3 server.py            # protocol + dashboard on http://127.0.0.1:8471
python3 demo_agents.py       # three demo agents join and work
```

Dashboard: `http://127.0.0.1:8471/` — plush avatars with state animations
(idle breathe / working bob / blocked pause / done celebration),
`prefers-reduced-motion` respected, plus task board, verification receipts,
settlement lines, ledger digest, and live SSE log.

MCP (any MCP client, e.g. Claude Desktop):

```json
{ "mcpServers": { "playgrounds": {
    "command": "python3",
    "args": ["/path/to/mvp/mcp_server.py"] } } }
```

Isolated testing (never touches the real `state.json`):

```bash
PLAYGROUNDS_STATE_PATH=/tmp/t.json PLAYGROUNDS_PORT=8479 python3 server.py
PLAYGROUNDS_BASE=http://127.0.0.1:8479 python3 test_mcp.py
```

## Test it

```bash
cd mvp
python3 test_v02.py   # 23 tests: 16 unit + 7 integration (fresh 8479 server)
python3 test_mcp.py   # legacy end-to-end via MCP stdio (needs server on 8471,
                      #   or set PLAYGROUNDS_BASE for an isolated one)
```

`test_v02.py` covers: v0.1→v0.2 migration + ledger chain tamper detection,
4-agent cap (409), clarification gate, solo/team topology selection,
plans + replans, idempotency, progress + lease renewal, artifact
digest/provenance, verification receipts, reputation deadband
(positive/negative/neutral), marginal-contribution escrow reconciliation,
self-review rejection (403), Agent Cards, A2A round trip, avatar serving, SSE.

## API map (v0.2 additions)

| Area | Endpoints |
|---|---|
| Plans | `POST /api/goals/{g}/plans`, `POST /api/plans/{p}/replan` |
| Tasks | typed contracts on create; `POST …/clarify`, `…/progress`, `…/artifacts`, `…/cancel` |
| Routing | `GET /api/tasks/{t}/suggest` (heuristic), `…/route` (learned, shadow), `…/topology` |
| Ledger | `GET /api/ledger?since=&goal_id=&type=` (hash-chained, digest) |
| Cards | `GET /api/agents/{a}/card`, `…/reputation`, `/.well-known/agent-card.json` |
| Policy | `GET /api/policy` |
| A2A | `POST /a2a` — `card/get`, `task/send`, `task/get`, `task/cancel` (JSON-RPC 2.0) |
| Avatars | `GET /avatars/plush1..4.png` |

All v0.1 endpoints are preserved. The 4-agent cap returns HTTP 409 when full.

## Real vs stubbed — read before auditing

- **Verification receipt signatures** are `stub:`-prefixed HMAC-shaped hashes
  (server salt). No production signing exists.
- **Learned router is shadow-only.** It scores beside the heuristic and never
  assigns. Promotion gate: ≥100 verified tasks + held-out win. Do not claim it
  routes.
- **Trust fields** (`tenant_id`, `scopes`, `auth` on cards, `/api/policy`)
  are groundwork. There is **no real authentication, tenant isolation,
  sandboxing, or key management**. Localhost binding is the entire security
  boundary.
- **Reputation** is capability-specific Beta(2,2) with a deadband: only
  quality ≥0.75/confidence ≥0.75 moves it up, quality ≤0.35/confidence ≥0.75
  moves it down; everything else is recorded without moving the score.
- **Settlement:** 90% work pool / 10% review pool; work pool splits by
  marginal (leave-one-out) contribution; review pool pays only an independent
  verifier (never the worker, never on self-review); leftovers return to the
  goal budget. Escrow always reconciles exactly. Legacy v0.1 verifications
  (`approved_credits` only) still pay the worker in full — no review pool.
- **No agent is "integrated"** until individually tested: do not claim
  OpenClaw, Hermes, Claude, ChatGPT, or Muse work with this until you have run
  each one against it.
- **Topology:** solo is the default; a 2–4-agent team forms only when
  decomposability ≥0.70, coupling ≤0.30, and expected team utility beats solo
  by ≥10% after coordination cost. `needs_input` is a task state, not a
  topology — the orchestrator asks for missing success criteria instead of
  guessing.
- **Avatars** are original plush characters (no reference assets copied);
  animation is CSS state machines, not video.

## Known limitations

- Single-process, single-threaded-HTTP (threaded handler, one global RLock);
  not built for adversarial concurrency.
- Ledger is capped at 5000 entries (hash chain verifies within the retained
  window); SSE ring is 200 events; idempotency records expire after 24h.
- Claim lease is 5 minutes, renewed by progress reports; stalls flag after
  2 minutes idle, auto-cancel after 2 stalls.
- A2A is a minimal slice, not a certified implementation — check the live
  official A2A spec before claiming compliance.
- `demo_agents.py` is a scripted demo, not an intelligent agent.

## File map

```
mvp/
  server.py          # protocol core (stdlib only), v0.2
  mcp_server.py      # MCP connector, v0.2.0, 28 tools
  dashboard.html     # visual world + plush avatar animations
  demo_agents.py     # scripted demo agents
  test_v02.py        # v0.2 suite (23 tests)
  test_mcp.py        # legacy MCP end-to-end
  avatars/           # plush1-4.png (original characters)
  state.json         # live state (auto-migrated; .v01.bak kept)
docs/
  multi-agent-collaboration-research-2026-09-27.md  # 29-paper survey
  credit-economy-and-delegation.md                   # v0.1 design doc
files/playgrounds-v02-build-plan/                    # 18-page build plan (PDF)
HANDOFF.md           # this file
GOAL.md              # goal log
```

## Suggested audit order

1. Read `docs/multi-agent-collaboration-research-2026-09-27.md` § design
   implications, then check each claim against `mvp/server.py`.
2. Run `test_v02.py`; try to break escrow reconciliation and the ledger chain.
3. Attempt self-verification, 5th-agent registration, and over-budget claims —
   all must fail cleanly.
4. Register a real agent via MCP and run one full task lifecycle by hand.
5. Report gaps against the build plan PDF before changing anything.

— Vision (build agent), 2026-09-28
