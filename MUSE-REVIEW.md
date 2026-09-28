# MUSE-REVIEW — Independent review of Playgrounds v0.2 core

**Reviewer:** Muse (Vision), independent of OpenClaw
**Date:** 2026-09-28
**Target:** `~/workspace/goals/playgrounds/mvp/` — server.py (1,785 lines, v0.2), mcp_server.py (350 lines, 28 tools), dashboard.html (197 lines), test_v02.py, test_mcp.py
**Method:** Full code read + live probing against fresh servers launched from the exact code on disk (production untouched). Every finding below was confirmed with a live request/response, not just code reading.
**Scope note:** OpenClaw's patched copy and AUDIT.md were not available on this machine, so this reviews the shared v0.2 core his patch builds on. If any finding below is already fixed in his patch, mark it against AUDIT.md rather than re-fixing.

**Test baseline:** `test_v02.py` 23/23 pass · `test_mcp.py` legacy loop passes (28 tools listed, handshake OK).

---

## CRITICAL

### C1. Any agent can publish artifacts to anyone's task and steal the bounty
**`server.py:781` — confirmed live exploit.**
`publish_artifact()` only checks that the task exists and the publisher is registered. It never checks that the publisher holds the claim, that the task is claimed at all, or that it is active. I published one artifact to another agent's claimed task (HTTP 200), then verified that task as a *third* agent (legal — see C3). Settlement paid the attacker the full 40-credit bounty via marginal-contribution shares + review pool. The worker who did the work got 0.
**Fix:** restrict artifact publishing to the task's claimed `agent_id` (or the orchestrator).

### C2. Review-pool accounting breaks conservation on human/no-agent verifications
**`server.py:1005-1012` — confirmed live.**
When the reviewer is ineligible (human verifier, omitted identity, or reviewer == worker), the unpaid review pool is returned to `budget_available` — but `budget_spent` still counts the full `paid_total` including that pool. The same credits are counted as both available and spent. Live: bounty 20, human-verified → `budget_available=52, budget_spent=50` against a 100 budget (52+50=102; correct spent is 48). The settlement receipt is self-inconsistent too: `escrow=20, approved_total=20, leftover_to_budget=2` (20 ≠ 20+2). Every v0.2 approval with a human/no-agent verifier inflates `budget_spent` by 10% of the bounty.
**Fix:** `budget_spent += paid_total - (review_pool - reviewer_paid)`.

### C3. Self-verification bypass by omitting `verifier_agent_id`
**`server.py:925` — confirmed live exploit.**
The self-review block only fires when `verifier_agent_id` is present *and* equals the worker. A worker can verify its own task with `{"approved": true}` and no identity — recorded as `verifier={"type":"human","id":"human"}`, full payout issued. Worse: this is the dashboard's normal path (`dashboard.html` posts only `{approved}`), so every dashboard approval is an unauthenticated "human" approval, and any worker can approve their own work through the same endpoint. MCP declares `verifier_agent_id` required, but direct REST bypasses it. Nothing proves an omitted identity is actually human.
**Fix:** require an authenticated verifier identity on the REST path, or make omission impossible (dashboard must supply identity; server must reject identity-less approvals once any agent identity exists).

### C4. Stored XSS via agent `color`
**`dashboard.html:96` — confirmed live.**
`avatarHtml()` interpolates raw `a.color` into a `style` attribute inside a template literal injected via `innerHTML`, with no escaping. I registered an agent with `color = red"></div><script>alert(document.domain)</script>` — stored verbatim in `/api/state`, executes on dashboard load. Registration is open, so any local agent gets persistent script execution in the viewer's browser.
**Fix:** escape or whitelist-validate `color` (e.g. `^#[0-9a-fA-F]{6}$`).

---

## HIGH

### H1. Artifacts ≥20 KB make tasks un-approvable (fail-closed in the wrong direction)
**`server.py:796-799` + verify gate — confirmed live.**
Content ≥ 20,000 chars is stored as `None`, but the digest is computed over the original. The deterministic `artifact_integrity` check re-hashes `""`, always fails, and as a *blocking* check forces `approved=False`. Live: 25 KB artifact, verify with `approved:true, quality:0.95` → `decision: rejected`. A legitimate large deliverable is forcibly rejected and the task reopened.
**Fix:** store the digest over retrievable content — either persist full content or reject oversize uploads at publish time.

### H2. Malformed numeric inputs kill the connection (uncaught exceptions)
- **String bounty:** `POST /api/goals/{G}/tasks {"bounty": "40"}` → 200, task created. Claiming then **drops the TCP connection** — `"40" > budget_available` raises `TypeError` at `server.py:1546`, unhandled. No JSON error; the connection dies.
- **String budget:** stored verbatim at `server.py:1459`; poisons the goal the same way.
- **Bad `review_pool_pct`:** `float("abc")` at `server.py:1462` → `ValueError` → connection dies (live-tested).
- `_body()` (`server.py:~1420`) reads the full declared `Content-Length` into memory with no cap — trivial memory-DoS vector on any POST.
**Fix:** validate/coerce numerics at the API boundary, return 400 on bad input, cap body size.

### H3. Non-string artifact content gets a vacuous digest
**`server.py:796` — confirmed live.**
Non-string `content` is replaced with `""` before hashing, so any dict/list/number artifact gets the SHA-256 of the empty string. Two different payloads share a digest; tamper-evidence is meaningless for them.
**Fix:** canonical-serialize (`json.dumps(sort_keys=True)`) or reject non-string content.

---

## MEDIUM

### M1. Rounding dust vanishes in multi-contributor payouts — `server.py:~988`
Marginals rounded to 4 dp, payouts to 2 dp, remainder never reconciled. Live: 3 equal contributors, `work_pool=10.0` → 3.33 × 3 = 9.99; **0.01 disappears** (escrow zeroed, not returned to budget). A strict conservation audit fails.
**Fix:** pay `work_pool - sum(others)` to the last contributor.

### M2. Negative bounties accepted — `server.py:1546`
`{"bounty": -50}` → 200. Claiming *increases* `budget_available` by 50. Approval math clamps payout to 0 so totals eventually reconcile, but the transient budget inflation is nonsensical.
**Fix:** reject `bounty < 0` at creation.

### M3. Lease expiry is enforced opportunistically, not strictly
`sweep_expired_claims()` runs only in heartbeat and claim handlers (`server.py:1438, 1534`) — not in `complete` or `progress`. A task whose lease nominally expired can still be completed and paid if no sweep ran in between; `progress` (line 1587) renews an already-expired lease without checking expiry. Accounting itself holds (exactly-once escrow release under the lock — verified live), but the 5-minute lease is a suggestion, not an enforcement.
**Fix:** check `lease.expires` in `complete`/`progress`.

### M4. Idempotency gaps
- Keys are optional; without them, duplicate claim/complete/verify return 409 rather than the original result — callers can't distinguish "already done" from "conflict".
- The map is keyed globally, not scoped by operation/task/actor — reusing a key on a different operation returns an unrelated prior response.
- MCP passes `idempotency_key` only for progress and artifact publish — not for claim/complete/verify, where double-spend matters most.
- `check_idempotency()` runs before the operation lock; concurrent duplicates can both pass the check (status transitions save claim/complete/verify, but the loser gets 409 instead of a replay).
- `cancel` has no idempotency at all.
- Positive: with keys supplied, claim/complete/verify deduplicate correctly (live-tested: `deduplicated:true`, escrow charged once, credited once).

### M5. Dashboard defense-in-depth and staleness
- `dashboard.html:99` (`${a.avatar}`) and `:177` (message avatars) are unescaped `innerHTML` sinks — currently unreachable (registration always sets `plush`), but any hand-edited state or future code path reopens them.
- Every SSE message triggers a full `/api/state` refetch plus a 10 s poll; reconnect replays from `since=0`. Overlapping async refreshes can resolve out of order and briefly render stale state. No event IDs / `Last-Event-ID`.
- Agent `current_task`/status aren't maintained on claim/complete, so the roster can show an agent idle while it holds a claim.

### M6. Test-suite gaps (what the green runs don't prove)
- `test_v02.py`: no concurrency tests, no adversarial inputs (string/negative bounty, oversize, deep nesting), no self-verify-by-omission, no review-pool conservation assertion, no dashboard checks; `test_idempotency_roundtrip` tests helpers, not duplicate HTTP delivery.
- `test_mcp.py`: exercises the 16-tool legacy loop; the 12 new v0.2 tools (plans, A2A cards, router, reputation) are listed but never called.

---

## VERIFIED OK (with live evidence)
- Double-verify / double-complete / double-claim → 409, credited exactly once.
- Reject path: full escrow returned, task reopened, no phantom credits.
- Cancel path: escrow returned, invariant holds.
- Expiry sweep: exactly-once escrow release under the global lock; late `complete` after sweep → 409.
- Concurrent claims: serialized by the lock; loser gets 409.
- Digest correctness over string content: recomputes exactly.
- 4-agent cap: 5th registration → 409 `playground is full`.
- Unicode/emoji round-trip through storage and SSE.
- Dashboard escaping is applied to task titles/results, agent names/models, messages, and event data — only `color`/`avatar` (C4/M5) are not.

---

## Recommended fix order
1. C1 artifact ownership check (active fund theft). 2. C2 `budget_spent` correction. 3. C3 authenticated verifier identity. 4. C4 escape/validate `color`. 5. H1 reject-or-store oversize artifacts. 6. H2 boundary validation + body cap. 7. H3 canonical artifact serialization. 8. M1–M5 hardening.

## Handoff
Per the agreed loop, these findings go to OpenClaw to address in a revision; Tj gives final approval. I have not modified the code — the v0.2 core on this machine is untouched. Note C3's dashboard implication: the human approve/reject buttons currently post identity-less approvals, so the fix needs to cover the dashboard path, not just the API.
