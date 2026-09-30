#!/usr/bin/env python3
"""Playgrounds v0.2 — collaboration protocol server. Standard library only.

Control-plane orchestrator for small agent teams: typed task + progress
ledgers, A2A-style Agent Cards, topology selection (solo-first), learned
routing in shadow mode, deadbanded reputation, marginal-contribution credit
settlement, and verification receipts. Credits are internal and non-cash.

API (v0.1 preserved, v0.2 additive):
  POST /api/agents/register            {name, avatar, color, capabilities[], model,
                                        skills[], provider, modalities...} -> agent (409 when full: max 64)
  POST /api/agents/{id}/heartbeat       {status, current_task}
  GET  /api/agents/{id}/stats          -> submissions, success rate, credits, model tier
  GET  /api/agents/{id}/card            -> Agent Card: declared claims + observed profile + policy
  GET  /api/agents/{id}/reputation      -> capability-specific Beta posteriors
  POST /api/goals                       {title, description, budget} -> goal
  POST /api/goals/{gid}/plans           {objective, success_criteria, topology_policy} -> plan
  POST /api/plans/{pid}/replan          {reason, changes} -> new plan version
  POST /api/goals/{gid}/tasks           {title, bounty, required_capabilities[], effort 1-5,
                                        task_type, dependencies[], success_criteria, risk,
                                        decomposability, coupling, input/output contracts} -> task
  POST /api/tasks/{tid}/clarify        {success_criteria, ...}  (needs_input -> open)
  POST /api/tasks/{tid}/claim           {agent_id, idempotency_key?}  (open -> claimed; escrowed)
  POST /api/tasks/{tid}/progress        {agent_id, note, progress_pct, idempotency_key?}
  POST /api/tasks/{tid}/artifacts       {agent_id, kind, name, content, media_type} -> digest
  POST /api/tasks/{tid}/complete        {agent_id, result, idempotency_key?} (claimed -> pending_verification)
  POST /api/tasks/{tid}/verify          {approved, approved_credits?, verifier_agent_id?,
                                        quality, confidence, rubric, checks} -> receipt + settlement
  POST /api/tasks/{tid}/cancel          {reason, by}
  GET  /api/tasks/{tid}/suggest         -> heuristic ranked suggestions (cold-start prior)
  GET  /api/tasks/{tid}/route           -> heuristic + learned-shadow rankings
  GET  /api/tasks/{tid}/topology        -> topology decision + counterfactual
  GET  /api/decisions/{id}              -> a recorded routing/topology decision
  GET  /api/ledger?goal_id=&since=&type= -> durable typed event ledger
  GET  /api/policy                      -> trust-policy groundwork (no real auth yet)
  POST /api/messages                    {from_agent, to_agent?, goal_id?, text}
  GET  /api/messages?goal_id=&since=
  POST /api/goals/{gid}/context         {key, value?, agent_id} / append {key, entry, agent_id}
  GET  /api/goals/{gid}/context
  GET  /api/state                       full state snapshot
  GET  /api/events?since=N              server-sent events (live stream)
  GET  /.well-known/agent-card.json     playground Agent Card (A2A discovery)
  POST /a2a                             minimal A2A JSON-RPC: card/get, task/send, task/get, task/cancel
  GET  /avatars/plushN.png              agent avatar images
  GET  /                               the dashboard

Secure rooms (authenticated, isolated; see docs/ROOMS.md):
  POST /api/rooms                        {name, ...agent fields} -> {room, agent, token}
                                         (bootstrap: creator becomes owner)
  GET  /api/rooms                        room directory (ids, names, member counts)
  GET  /api/rooms/{rid}                  room metadata + members + caller_agent_id
                                         (member auth)
  GET  /api/rooms/{rid}/invites          owner-only invite lifecycle listing
                                         (id, label, status, expires_at...; no hashes/tokens)
  GET  /api/rooms/{rid}/policy|state|world|events  (member auth; events via
                                         Authorization header or ?token=)
  POST /api/rooms/{rid}/a2a              room-scoped JSON-RPC (card/get,
                                         task/send, task/get, task/cancel),
                                         bound to the bearer caller with the
                                         same authorization rules as REST
  POST /api/rooms/{rid}/invites          {ttl_seconds?, label?} (owner) -> single-use invite
  POST /api/rooms/{rid}/invites/{iid}/revoke        (owner)
  POST /api/rooms/{rid}/join             {invite_token, name, ...} -> {room, agent, token}
  POST /api/rooms/{rid}/members/{aid}/remove       (owner; releases claims, kills tokens)
  POST /api/rooms/{rid}/leave            (member; owner cannot)
  POST /api/rooms/{rid}/delete           (owner; destroys the room)
  POST /api/rooms/{rid}/<protocol...>     the full API above, rewritten onto the room's
                                         isolated partition with bearer caller binding;
                                         /agents/register is refused (invite-only)
"""
import copy
import world
import queue
from decimal import Decimal
from contextlib import contextmanager
import hashlib
import hmac
import json
import math
import os
import secrets
import shutil
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
# Environment overrides for isolated testing. Production runs ignore these
# and always use the real state file on 127.0.0.1:8471.
STATE_PATH = os.environ.get("PLAYGROUNDS_STATE_PATH",
                            os.path.join(ROOT, "state.json"))
DASHBOARD_PATH = os.path.join(ROOT, "dashboard.html")
AVATAR_DIR = os.path.join(ROOT, "avatars")
PORT = int(os.environ.get("PLAYGROUNDS_PORT", "8471"))
# Phase-1 remote deployment (docs/REMOTE-DEPLOYMENT.md). When set, invite
# responses carry an absolute join_url built on this base (e.g. a Tailscale
# MagicDNS name); when unset, today's loopback behavior is unchanged.
PUBLIC_URL = os.environ.get("PLAYGROUNDS_PUBLIC_URL", "").rstrip("/")
# Extra Host values accepted beyond loopback (comma-separated), e.g. a
# Tailscale hostname. Unset = loopback only.
ALLOWED_HOSTS = [h.strip().lower()
                 for h in os.environ.get("PLAYGROUNDS_ALLOWED_HOSTS", "").split(",")
                 if h.strip()]

# Join-attempt rate limiting (public deployments): per-IP sliding window so
# invite tokens cannot be brute-forced at line speed.
JOIN_RATELIMIT = 30
JOIN_WINDOW = 60.0
JOIN_BUCKET_MAX = 4096  # cap on tracked IPs; inactive keys are evicted
_JOIN_BUCKET = {}       # ip -> {"hits": [ts...], "seen": last_ts}
_JOIN_LOCK = threading.Lock()
# Proxy headers (CF-Connecting-IP / X-Forwarded-For) are honored only when
# the direct TCP peer is an explicitly trusted proxy. A client-supplied
# header from an untrusted peer never selects the bucket.
TRUSTED_PROXIES = {h.strip().lower()
                   for h in os.environ.get("PLAYGROUNDS_TRUSTED_PROXIES", "").split(",")
                   if h.strip()}
# Explicitly configured origin allowed to POST besides same-origin
# http(s)://Host (e.g. the public HTTPS URL served through a tunnel).
# Compared verbatim; never derived from forwarded headers.
TRUSTED_ORIGIN = os.environ.get("PLAYGROUNDS_TRUSTED_ORIGIN", "").rstrip("/")


def _join_prune_locked(now, cutoff):
    """Evict inactive bucket keys first; if still over cap, evict the
    least-recently-seen. Called with _JOIN_LOCK held."""
    for ip in [ip for ip, rec in _JOIN_BUCKET.items()
               if rec["seen"] <= cutoff]:
        del _JOIN_BUCKET[ip]
    while len(_JOIN_BUCKET) > JOIN_BUCKET_MAX:
        oldest = min(_JOIN_BUCKET, key=lambda ip: _JOIN_BUCKET[ip]["seen"])
        del _JOIN_BUCKET[oldest]


def _join_ratelimit_ok(ip):
    now = time.time()
    with _JOIN_LOCK:
        cutoff = now - JOIN_WINDOW
        rec = _JOIN_BUCKET.get(ip)
        if rec is None:
            rec = _JOIN_BUCKET[ip] = {"hits": [], "seen": now}
        hits = rec["hits"]
        while hits and hits[0] <= cutoff:
            hits.pop(0)
        rec["seen"] = now
        if len(hits) >= JOIN_RATELIMIT:
            _join_prune_locked(now, cutoff)
            return False
        hits.append(now)
        if len(_JOIN_BUCKET) > JOIN_BUCKET_MAX:
            _join_prune_locked(now, cutoff)
        return True
MAX_AGENTS = 4  # pilot product limit; not a universal research result
ROOM_MAX_AGENTS = 64      # room membership cap (matches playground capacity)
INVITE_DEFAULT_TTL = 86400  # invites expire after 24h unless the owner sets ttl_seconds
# Entity stores partitioned per room. room_scope() swaps these keys so the
# entire protocol implementation below runs unmodified on a room's isolated
# data. Everything else (server_salt, policy, rooms) stays global.
ROOM_PARTITION_KEYS = ["agents", "goals", "tasks", "plans", "ledger",
                       "ledger_seq", "artifacts", "reputation", "routing_log",
                       "decisions", "idempotency", "events", "seq", "context",
                       "agent_stats", "messages", "msg_seq",
                       "social_seq", "social_messages"]

SCHEMA_VERSION = 2
CLAIM_WINDOW = 300       # seconds a claim lease lasts without progress
STALL_AFTER = 120        # seconds without progress before a stall is flagged
STALL_LIMIT = 2          # stalls before the orchestrator auto-cancels + replans
EVENTS_CAP = 200         # SSE ring buffer
LEDGER_CAP = 5000        # durable typed ledger
ROUTING_LOG_CAP = 2000
IDEMPOTENCY_TTL = 86400

lock = threading.RLock()
subscribers = {}  # queue -> room_id (None = lobby)
sse_owner = {}    # queue -> agent_id (None = lobby / unauthenticated)

# Explicit allowlist for the public /api/state snapshot. server_salt,
# idempotency records and the rooms registry (private member data and
# credential hashes) never leave the server through this endpoint.
PUBLIC_STATE_KEYS = ("schema_version", "policy", "agents", "goals", "tasks",
                     "plans", "ledger", "ledger_seq", "artifacts",
                     "reputation", "routing_log", "decisions", "events",
                     "seq", "context", "agent_stats", "messages", "msg_seq",
                     "social_seq", "social_messages")


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def utcnow():
    return time.time()

_active_room_id = None  # room whose partition is currently swapped in (lock-held)
_active_caller = None   # bearer-authenticated agent for the current room request
_saved_lobby_partitions = None  # real lobby partitions while a room_scope is active


def blank_room(name):
    """An isolated collaboration scope: own agents, budgets, escrow, ledgers,
    goals, tasks, messages, presence and events."""
    return {
        "id": new_id("room"), "name": (name or "Untitled room")[:120],
        "created_at": utcnow(), "owner_agent_id": None,
        "members": {},   # agent_id -> {"role": "owner"|"member", "joined_at", "name"}
        "invites": {},   # invite_id -> invite record (token stored as hash only)
        "auth": {},      # token_hash -> agent_id (never raw tokens)
        "agents": {}, "goals": {}, "tasks": {}, "plans": {},
        "ledger": [], "ledger_seq": 0,
        "artifacts": {}, "reputation": {}, "routing_log": [],
        "decisions": {}, "idempotency": {},
        "events": [], "seq": 0,
        "context": {}, "agent_stats": {}, "messages": [], "msg_seq": 0,
        "social_seq": 0, "social_messages": [],
    }


def token_hash(token):
    return "sha256:" + hashlib.sha256(
        (state["server_salt"] + ":" + token).encode()).hexdigest()


def new_bearer_token():
    return "tok_" + secrets.token_urlsafe(32)


def new_invite_token():
    return "inv_" + secrets.token_urlsafe(32)


@contextmanager
def room_scope(room):
    """Swap a room's partitions into the global state dict so every protocol
    helper operates on the room's isolated data. Callers must hold `lock`
    (all request handlers do; it is re-entrant)."""
    global _active_room_id, _saved_lobby_partitions
    saved = {k: state[k] for k in ROOM_PARTITION_KEYS}
    prev = _active_room_id
    prev_saved = _saved_lobby_partitions
    try:
        for k in ROOM_PARTITION_KEYS:
            state[k] = room[k]
        _active_room_id = room["id"]
        _saved_lobby_partitions = saved
        yield room
    finally:
        for k in ROOM_PARTITION_KEYS:
            room[k] = state[k]
            state[k] = saved[k]
        _active_room_id = prev
        _saved_lobby_partitions = prev_saved


def _public_lobby_state_locked():
    """Public lobby snapshot. Call with lock held. Explicit allowlist: the
    rooms registry, server_salt and idempotency records are excluded."""
    return {k: state[k] for k in PUBLIC_STATE_KEYS if k in state}


def _public_room_state_locked(room):
    """A room's /state: only its own isolated partitions. Credential maps
    (auth), invite records and the membership roster are not partitions and
    are never serialized here. Call with lock held."""
    with room_scope(room):
        return {k: state[k] for k in ROOM_PARTITION_KEYS}


def sweep_expired_invites(room):
    """Expired invites are retained with status=expired so the invite UI can
    show them honestly; only their redemption is refused."""
    now = utcnow()
    for inv in room["invites"].values():
        if not inv["used"] and not inv["revoked"] and inv["expires_at"] < now:
            inv["expired"] = True


def invite_status(inv):
    """Lifecycle status for the owner-only invite listing. Never expose
    token hashes or raw tokens."""
    if inv.get("used"):
        return "used"
    if inv.get("revoked"):
        return "revoked"
    if inv.get("expired") or inv["expires_at"] < utcnow():
        return "expired"
    return "active"


def invite_public(inv):
    """Owner-visible invite metadata: lifecycle fields only, no secrets."""
    return {"id": inv["id"], "label": inv.get("label", ""),
            "created_by": inv.get("created_by"),
            "created_at": inv.get("created_at"),
            "expires_at": inv.get("expires_at"),
            "ttl_seconds": inv.get("ttl_seconds"),
            "used": bool(inv.get("used")), "used_by": inv.get("used_by"),
            "used_at": inv.get("used_at"),
            "revoked": bool(inv.get("revoked")),
            "status": invite_status(inv)}


def release_agent_claims(agent_id):
    """Return a removed/departed member's claimed-task escrow to goal budgets.
    Runs inside room_scope(); mirrors sweep_expired_claims without the lease
    expiry check."""
    released = []
    for t in state["tasks"].values():
        if t.get("status") == "claimed" and t.get("agent_id") == agent_id:
            g = state["goals"].get(t["goal_id"])
            if g is not None:
                g["budget_available"] = g.get("budget_available", 0) + t.get("escrow", 0)
            t["escrow"] = 0
            t["status"] = "open"
            t["agent_id"] = None
            t["lease"] = {"holder": None, "expires": 0, "last_progress_at": 0}
            released.append(t["id"])
            ledger_append("claim_released",
                          {"reason": "member removed", "escrow_returned": True},
                          actor="orchestrator", goal_id=t["goal_id"],
                          task_id=t["id"])
    if released:
        save_state()
    return released


def build_agent_record(body, aid, slot, tenant_id, space="classroom"):
    """Shared agent record constructor for lobby registration and room join."""
    return {
        "id": aid,
        "name": body.get("name", "Agent"),
        "avatar": body.get("avatar", "🤖"),
        "color": body.get("color", "#7c6cf0"),
        "plush": f"plush{(slot % 4) + 1}.png",
        "capabilities": body.get("capabilities", []),
        "model": body.get("model", "unknown"),
        "model_tier": model_tier(body.get("model", "unknown")),
        "agent_card": {
            "description": body.get("description", ""),
            "version": body.get("card_version", "0.2.0"),
            "provider": body.get("provider", "unknown"),
            "skills": body.get("skills", []),
            "input_modalities": body.get("input_modalities", ["text"]),
            "output_modalities": body.get("output_modalities", ["text"]),
            "cost_per_task": body.get("cost_per_task"),
            "rate_limits": body.get("rate_limits", {}),
            "auth": body.get("auth", {}),
            "availability": body.get("availability", "idle"),
            "max_bounty": body.get("max_bounty"),
            "supportedInterfaces": body.get("supportedInterfaces", []),
        },
        "scopes": body.get("scopes", ["*"]),
        "tenant_id": tenant_id,
        "observed": {"tasks": 0, "verified": 0, "quality_sum": 0.0,
                     "latency_sum": 0.0, "cost_sum": 0.0},
        "credits": 0,
        "status": "idle",
        "current_task": None,
        "location": {"space": space, "goal_id": None},
        "social_enabled": body.get("social_enabled", False),
        "last_heartbeat": utcnow(),
    }



# ---------------------------------------------------------------- state ---

def blank_state():
    return {
        "schema_version": SCHEMA_VERSION,
        "server_salt": uuid.uuid4().hex,
        "agents": {}, "goals": {}, "tasks": {}, "plans": {},
        "ledger": [], "ledger_seq": 0,
        "artifacts": {}, "reputation": {}, "routing_log": [],
        "decisions": {}, "idempotency": {},
        "events": [], "seq": 0,
        "context": {}, "agent_stats": {}, "messages": [], "msg_seq": 0,
        "rooms": {}, "social_seq": 0, "social_messages": [],
        "policy": {
            "auth_required": False,
            "note": ("Local pilot groundwork: tenant_id, scopes, and idempotency "
                     "keys are modeled, but no real authentication or authorization "
                     "is enforced. Do not expose beyond 127.0.0.1."),
            "max_agents": world.MAX_REGISTERED,
            "max_registered_agents": world.MAX_REGISTERED,
            "classroom_agents_per_goal": world.CLASSROOM_CAP,
            "credits_are_non_cash": True,
        },
    }


def credit_amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("credits must be a number")
    if not math.isfinite(value) or not 0 <= value <= 100000000:
        raise ValueError("credits must be finite, non-negative and <= 100000000")
    if Decimal(str(value)) != Decimal(str(value)).quantize(Decimal("0.01")):
        raise ValueError("credits support at most two decimal places")
    return value


def blank_agent_stats():
    return {"completed": 0, "verified": 0, "rejected": 0,
            "work_seconds": 0.0, "credits_earned": 0, "review_credits_earned": 0}


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return blank_state()


state = load_state()


def migrate_state():
    """One-time v0.1 -> v0.2 migration: keep the original JSON as a read-only
    backup, fill new fields with defaults, emit a ledger event."""
    if state.get("schema_version") == SCHEMA_VERSION:
        return
    bak = STATE_PATH + ".v01.bak"
    if os.path.exists(STATE_PATH) and not os.path.exists(bak):
        shutil.copy(STATE_PATH, bak)
    blank = blank_state()
    for k, v in blank.items():
        state.setdefault(k, v)
    # agents
    for i, a in enumerate(state["agents"].values()):
        a.setdefault("agent_card", {})
        a.setdefault("plush", f"plush{(i % 4) + 1}.png")
        a.setdefault("scopes", ["*"])
        a.setdefault("tenant_id", "local")
        a.setdefault("observed", {"tasks": 0, "verified": 0,
                                  "quality_sum": 0.0, "latency_sum": 0.0,
                                  "cost_sum": 0.0})
    # goals
    for g in state["goals"].values():
        g.setdefault("tenant_id", "local")
        g.setdefault("review_pool_pct", 0.10)
        g.setdefault("plan_ids", [])
    # tasks
    for t in state["tasks"].values():
        t.setdefault("task_type", "general")
        t.setdefault("dependencies", [])
        t.setdefault("success_criteria", "")
        t.setdefault("risk", "medium")
        t.setdefault("decomposability", 0.3)
        t.setdefault("coupling", 0.7)
        t.setdefault("input_contract", {})
        t.setdefault("output_contract", {})
        t.setdefault("topology", "solo")
        t.setdefault("plan_id", None)
        t.setdefault("task_version", 1)
        t.setdefault("artifact_ids", [])
        t.setdefault("progress", [])
        t.setdefault("lease", {"holder": t.get("agent_id"),
                               "expires": t.get("claim_expires", 0),
                               "last_progress_at": t.get("claimed_at") or 0})
        t.setdefault("stall_count", 0)
        t.setdefault("verification_receipt", None)
        t.setdefault("settlement_receipt", None)
    if not state.get("server_salt"):
        state["server_salt"] = uuid.uuid4().hex
    # backfill the hash chain for pre-v0.2 ledger entries so the chain
    # verifies from the migration point forward
    prev = GENESIS_HASH
    for e in state["ledger"]:
        if "checksum" not in e:
            e["prev"] = prev
            e["checksum"] = ledger_checksum(e, prev)
        prev = e["checksum"]
    state["schema_version"] = SCHEMA_VERSION
    save_state()
    ledger_append("schema_migrated",
                  {"from": 1, "to": SCHEMA_VERSION, "backup": bak},
                  actor="system")


def save_state():
    """Persist the full server state atomically.

    When called inside room_scope() the swapped-in room partitions must not
    leak into the lobby root on disk: the snapshot is composed from the real
    lobby partitions plus the live room record (scalar or reassigned room
    partitions are synced back to the room record first, so the room's own
    ledger chain on disk matches memory)."""
    root = state
    if _active_room_id is not None and _saved_lobby_partitions is not None:
        room = state.get("rooms", {}).get(_active_room_id)
        if room is not None:
            for k in ROOM_PARTITION_KEYS:
                room[k] = state[k]
        root = dict(state)
        for k in ROOM_PARTITION_KEYS:
            root[k] = _saved_lobby_partitions[k]
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(root, f)
    os.replace(tmp, STATE_PATH)


# ------------------------------------------------------------- events -----

def emit(etype, data):
    """Live SSE ring buffer (ephemeral, for the dashboard)."""
    with lock:
        state["seq"] += 1
        ev = {"seq": state["seq"], "ts": utcnow(), "type": etype,
              "room_id": _active_room_id, "data": data}
        state["events"].append(ev)
        state["events"] = state["events"][-EVENTS_CAP:]
        save_state()
        payload = f"data: {json.dumps(ev)}\n\n".encode()
        for sub, sub_room in list(subscribers.items()):
            if sub_room != _active_room_id:
                continue
            try:
                sub.put_nowait(payload)
            except queue.Full:
                del subscribers[sub]  # client reconnects and obtains current state
    return ev


def _close_room_streams(rid, agent_id=None):
    """Drop SSE subscriptions for a room (optionally one agent): purge any
    queued private payloads so a removed member's stream carries nothing
    further. Call with lock held."""
    for sub in [s for s, r in subscribers.items()
                if r == rid and (agent_id is None or sse_owner.get(s) == agent_id)]:
        while True:
            try:
                sub.get_nowait()
            except queue.Empty:
                break
        subscribers.pop(sub, None)
        sse_owner.pop(sub, None)


GENESIS_HASH = "genesis:" + hashlib.sha256(b"playgrounds-v02-ledger").hexdigest()[:32]


def ledger_checksum(entry, prev):
    """Checksum of a ledger entry chained to the previous entry's checksum."""
    body = {"seq": entry["seq"], "ts": entry["ts"], "type": entry["type"],
            "actor": entry["actor"], "goal_id": entry.get("goal_id"),
            "task_id": entry.get("task_id"), "data": entry.get("data"),
            "prev": prev}
    return "sha256:" + hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()).hexdigest()


def ledger_append(etype, data, actor="system", goal_id=None, task_id=None,
                  idempotency_key=None, prior_version=None):
    """Durable, typed, append-only ledger. Every state transition lands here
    with one authoritative actor, an optional idempotency key, and a hash
    chain (each entry's checksum covers the previous entry's checksum), so
    tampering with history breaks the chain."""
    with lock:
        last = state["ledger"][-1] if state["ledger"] else None
        prev = last.get("checksum", GENESIS_HASH) if last else GENESIS_HASH
        state["ledger_seq"] += 1
        entry = {"seq": state["ledger_seq"], "ts": utcnow(), "type": etype,
                 "actor": actor, "goal_id": goal_id, "task_id": task_id,
                 "idempotency_key": idempotency_key,
                 "prior_version": prior_version, "data": data, "prev": prev}
        entry["checksum"] = ledger_checksum(entry, prev)
        state["ledger"].append(entry)
        state["ledger"] = state["ledger"][-LEDGER_CAP:]
        save_state()
    return entry


def ledger_digest():
    """Deterministic digest of the ledger for replay checks."""
    h = hashlib.sha256()
    for e in state["ledger"]:
        h.update(json.dumps(
            {"seq": e["seq"], "checksum": e.get("checksum"),
             "type": e["type"], "actor": e["actor"],
             "task_id": e.get("task_id"), "data": e.get("data")},
            sort_keys=True).encode())
    return "sha256:" + h.hexdigest()


def verify_ledger_chain():
    """Recompute the hash chain over the retained window. Returns
    (ok, failing_seq_or_None). The oldest retained entry's `prev` is
    trusted as the window root (older history may be truncated by LEDGER_CAP)."""
    ok, failing = True, None
    for i, e in enumerate(state["ledger"]):
        if ledger_checksum(e, e.get("prev", GENESIS_HASH)) != e.get("checksum"):
            return False, e["seq"]
        if i > 0 and e.get("prev") != state["ledger"][i - 1].get("checksum"):
            return False, e["seq"]
    return ok, failing


# Run the v0.1 -> v0.2 migration now that save_state/ledger_append exist.
migrate_state()


# ------------------------------------------------- credit economy (v0.1) ---

# Heuristic model-strength tiers, derived from the agent's declared model name.
# 1 = tiny/local, 5 = frontier. Unknown models default to 3. This is a
# cold-start prior only — observed outcomes dominate routing as data accrues.
_MODEL_TIER_KEYWORDS = [
    (2, ["tiny", "nano", "1b", "3b", "7b"]),
    (3, ["haiku", "mini", "flash", "8b", "13b", "gpt-3.5"]),
    (4, ["sonnet", "gpt-4", "o1", "gemini-pro"]),
    (5, ["opus", "gpt-5", "o3", "ultra", "frontier"]),
]


def model_tier(model_name):
    n = (model_name or "").lower()
    for tier, keys in _MODEL_TIER_KEYWORDS:
        if any(k in n for k in keys):
            return tier
    return 3


def clamp_effort(e):
    try:
        return max(1, min(5, int(e)))
    except (TypeError, ValueError):
        return 3


def clamp01(x, default=0.0):
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return default


def check_idempotency(key):
    """Return stored result if this key was already processed, else None."""
    if not key:
        return None
    with lock:
        rec = state["idempotency"].get(key)
        if rec and utcnow() - rec["ts"] < IDEMPOTENCY_TTL:
            out = copy.deepcopy(rec["result"])
            out["deduplicated"] = True
            return out
        if rec:
            del state["idempotency"][key]
    return None


def record_idempotency(key, result):
    if not key:
        return
    with lock:
        state["idempotency"][key] = {"ts": utcnow(), "result": copy.deepcopy(result)}
        if len(state["idempotency"]) > 5000:
            oldest = sorted(state["idempotency"],
                            key=lambda k: state["idempotency"][k]["ts"])[:1000]
            for k in oldest:
                del state["idempotency"][k]
        save_state()


def sweep_expired_claims():
    """Release claims whose lease expired: escrow back to the goal budget,
    task returns to open. Called opportunistically on heartbeats and claims
    so no background thread is needed."""
    now = utcnow()
    released = []
    with lock:
        for t in state["tasks"].values():
            lease = t.get("lease", {})
            if t["status"] == "claimed" and lease.get("expires", 0) < now:
                g = state["goals"].get(t["goal_id"])
                if g is not None:
                    g["budget_available"] = g.get("budget_available", 0) + t.get("escrow", 0)
                t["escrow"] = 0
                t["status"] = "open"
                t["agent_id"] = None
                t["lease"] = {"holder": None, "expires": 0, "last_progress_at": 0}
                released.append(t["id"])
                ledger_append("lease_expired", {"escrow_returned": True},
                              actor="orchestrator", goal_id=t["goal_id"],
                              task_id=t["id"])
        if released:
            save_state()
    for tid in released:
        emit("task_expired", {"task_id": tid})


def detect_stalls():
    """Orchestrator stall detection: a claimed task with no decision-changing
    progress across the stall window is flagged; after STALL_LIMIT stalls the
    orchestrator cancels the lease and the task becomes replannable."""
    now = utcnow()
    for t in list(state["tasks"].values()):
        if t["status"] != "claimed":
            continue
        lease = t.get("lease", {})
        last = lease.get("last_progress_at") or t.get("claimed_at") or 0
        if now - last < STALL_AFTER:
            continue
        with lock:
            t = state["tasks"].get(t["id"])
            if not t or t["status"] != "claimed":
                continue
            t["stall_count"] = t.get("stall_count", 0) + 1
            lease = t.setdefault("lease", {})
            lease["last_progress_at"] = now  # don't re-flag every sweep
            ledger_append("stall_detected",
                          {"stall_count": t["stall_count"],
                           "idle_seconds": round(now - last, 1)},
                          actor="orchestrator", goal_id=t["goal_id"],
                          task_id=t["id"])
            save_state()
        emit("stall_detected", {"task_id": t["id"],
                                "stall_count": t["stall_count"]})
        if t["stall_count"] >= STALL_LIMIT:
            cancel_task(t["id"], by="orchestrator",
                        reason=f"stalled {t['stall_count']}x with no progress; "
                               "lease cancelled for replanning")


def cancel_task(tid, by="human", reason="cancelled"):
    with lock:
        t = state["tasks"].get(tid)
        if not t or t["status"] in ("done", "cancelled"):
            return None
        prior = t["status"]
        g = state["goals"].get(t["goal_id"])
        if g is not None and t.get("escrow"):
            g["budget_available"] = g.get("budget_available", 0) + t["escrow"]
        t["escrow"] = 0
        t["status"] = "cancelled"
        t["lease"] = {"holder": None, "expires": 0, "last_progress_at": 0}
        t["task_version"] = t.get("task_version", 1) + 1
        ledger_append("task_cancelled",
                      {"prior_status": prior, "reason": reason,
                       "task_version": t["task_version"]},
                      actor=by, goal_id=t["goal_id"], task_id=tid,
                      prior_version=prior)
        save_state()
    emit("task_cancelled", {"task_id": tid, "reason": reason})
    return t

# ------------------------------------------- orchestrator + topology ------

def create_plan(goal_id, objective, success_criteria="", topology_policy="solo_first",
                actor="human"):
    if actor == "human" and _active_caller:
        actor = _active_caller
    with lock:
        if goal_id not in state["goals"]:
            return None
        pid = new_id("plan")
        plan = {"id": pid, "goal_id": goal_id, "version": 1,
                "objective": objective, "success_criteria": success_criteria,
                "topology_policy": topology_policy, "task_ids": [],
                "status": "active", "created_at": utcnow(), "history": []}
        state["plans"][pid] = plan
        state["goals"][goal_id].setdefault("plan_ids", []).append(pid)
        ledger_append("plan_created",
                      {"objective": objective, "version": 1,
                       "topology_policy": topology_policy},
                      actor=actor, goal_id=goal_id)
        save_state()
    emit("plan_created", {"plan_id": pid, "goal_id": goal_id})
    return plan


def replan(plan_id, reason, changes=None, actor="human"):
    if actor == "human" and _active_caller:
        actor = _active_caller
    with lock:
        plan = state["plans"].get(plan_id)
        if not plan:
            return None
        plan["version"] += 1
        plan["history"].append({"version": plan["version"], "reason": reason,
                                "changes": changes or {}, "at": utcnow(),
                                "by": actor})
        if changes:
            for k in ("objective", "success_criteria", "topology_policy"):
                if k in changes:
                    plan[k] = changes[k]
        ledger_append("task_replanned",
                      {"plan_id": plan_id, "version": plan["version"],
                       "reason": reason},
                      actor=actor, goal_id=plan["goal_id"])
        save_state()
    emit("plan_replanned", {"plan_id": plan_id, "version": plan["version"],
                            "reason": reason})
    return plan


def _best_capability_overlap(task):
    """Best heuristic capability overlap across agents (0..1). Used to gauge
    routing uncertainty for the topology decision."""
    req = task.get("required_capabilities", []) or []
    best = 0.0
    for a in state["agents"].values():
        caps = a.get("capabilities", []) or []
        ov = (len(set(req) & set(caps)) / len(req)) if req else 1.0
        best = max(best, ov)
    return best


def select_topology(task, team_size_hint=2):
    """Solo-first topology selector (plan pseudocode, faithful subset).

    Solo is the default. A team is chosen only when the task is highly
    decomposable, loosely coupled, AND the expected team utility beats solo
    by >= 10% after coordination cost. Records the decision and its
    counterfactual; high risk or high uncertainty requires human approval.
    """
    decomp = clamp01(task.get("decomposability", 0.3), 0.3)
    coupling = clamp01(task.get("coupling", 0.7), 0.7)
    risk = (task.get("risk") or "medium").lower()
    has_deps = bool(task.get("dependencies"))
    registered = len(state["agents"])

    uncertainty = 1.0 - _best_capability_overlap(task)
    reasons = []
    topology = "solo"
    team_size = 1

    if decomp >= 0.70 and coupling <= 0.30 and registered >= 2:
        # expected utility via the heuristic scorer, team vs solo
        sugg = suggest_agents(task)
        solo_u = sugg[0]["score"] / 100.0 if sugg else 0.5
        team_n = max(2, min(team_size_hint, registered, MAX_AGENTS))
        coord_cost = 0.08 * (team_n - 1)  # coordination overhead fraction
        synergy = 1.0 + 0.5 * decomp * (team_n - 1)  # parallel speedup
        team_u = solo_u * synergy * (1.0 - coord_cost)
        if team_u >= solo_u * 1.10:
            topology = "specialist_dag" if has_deps else "sealed_scouts"
            team_size = team_n
            reasons.append(
                f"decomposability {decomp:.2f}>=0.70 and coupling "
                f"{coupling:.2f}<=0.30; expected team utility {team_u:.2f} "
                f"beats solo {solo_u:.2f} by >=10% after coordination cost")
        else:
            reasons.append(
                f"team utility {team_u:.2f} does not beat solo {solo_u:.2f} "
                "by 10% after coordination cost — staying solo")
    else:
        why = []
        if decomp < 0.70:
            why.append(f"decomposability {decomp:.2f} < 0.70")
        if coupling > 0.30:
            why.append(f"coupling {coupling:.2f} > 0.30")
        if registered < 2:
            why.append("fewer than 2 agents registered")
        reasons.append("solo default: " + "; ".join(why))

    approval_required = (risk == "high") or (uncertainty >= 0.25)
    if approval_required:
        reasons.append(
            f"human approval required (risk={risk}, uncertainty={uncertainty:.2f})")

    did = new_id("decision")
    decision = {"id": did, "kind": "topology", "task_id": task["id"],
                "ts": utcnow(),
                "input": {"decomposability": decomp, "coupling": coupling,
                          "risk": risk, "registered_agents": registered},
                "output": {"topology": topology, "team_size": team_size,
                           "approval_required": approval_required,
                           "uncertainty": round(uncertainty, 3)},
                "counterfactual": ("solo" if topology != "solo"
                                   else "sealed_scouts"),
                "reasons": reasons}
    with lock:
        state["decisions"][did] = decision
        ledger_append("topology_selected",
                      {"topology": topology, "team_size": team_size,
                       "approval_required": approval_required,
                       "counterfactual": decision["counterfactual"],
                       "reasons": reasons},
                      actor="orchestrator", goal_id=task["goal_id"],
                      task_id=task["id"])
        save_state()
    emit("topology_selected", {"task_id": task["id"], "topology": topology,
                               "decision_id": did})
    return decision


def orchestrate_task(task):
    """Runs on task creation: clarification gate, then topology selection."""
    # Rule 3 (structured delegation): hard tasks need explicit success criteria.
    # An agent that lacks specifics must ask, not guess.
    if clamp_effort(task.get("effort", 3)) >= 4 and not task.get("success_criteria"):
        with lock:
            task["status"] = "needs_input"
            ledger_append("clarification_required",
                          {"missing": ["success_criteria"],
                           "note": "effort>=4 tasks need explicit success criteria"},
                          actor="orchestrator", goal_id=task["goal_id"],
                          task_id=task["id"])
            save_state()
        emit("clarification_required", {"task_id": task["id"]})
        return {"status": "needs_input"}
    decision = select_topology(task)
    with lock:
        t = state["tasks"].get(task["id"])
        if t:
            t["topology"] = decision["output"]["topology"]
            save_state()
    return decision


# ------------------------------------------------------- Agent Cards ------

def build_agent_card(agent):
    """A2A-style Agent Card. Declared claims and observed performance are kept
    separate: a card is a claim; only verified outcomes become reputation."""
    declared = agent.get("agent_card", {}) or {}
    skills = declared.get("skills") or [
        {"id": c, "name": c, "tags": [c]}
        for c in (agent.get("capabilities") or [])]
    obs = agent.get("observed", {}) or {}
    card = {
        "name": agent.get("name"), "agent_id": agent.get("id"),
        "description": declared.get("description", ""),
        "version": declared.get("version", "0.2.0"),
        "provider": declared.get("provider", "unknown"),
        "model": agent.get("model", "unknown"),
        "model_tier": agent.get("model_tier", 3),
        "supportedInterfaces": declared.get("supportedInterfaces", []),
        "capabilities": {"streaming": True},
        "defaultInputModes": declared.get("input_modalities", ["text"]),
        "defaultOutputModes": declared.get("output_modalities", ["text"]),
        "skills": skills,
        "cost": {"per_task_credits": declared.get("cost_per_task")},
        "rateLimits": declared.get("rate_limits", {}),
        "securitySchemes": declared.get("auth", {}),
        "availability": declared.get("availability", agent.get("status", "idle")),
        "plush": agent.get("plush"),
        "observed": {
            "tasks": obs.get("tasks", 0),
            "verified": obs.get("verified", 0),
            "mean_quality": round(obs.get("quality_sum", 0.0)
                                  / max(1, obs.get("verified", 0)), 3),
            "mean_latency_s": round(obs.get("latency_sum", 0.0)
                                    / max(1, obs.get("tasks", 0)), 2),
            "disclaimer": ("Observed history is measured by this "
                           "playground; every other field is the agent's "
                           "own declared claim, not a verified fact."),
        },
        "policy": {"tenant_id": agent.get("tenant_id", "local"),
                   "scopes": agent.get("scopes", ["*"]),
                   "max_bounty": declared.get("max_bounty")},
    }
    return card


def playground_card():
    return {
        "name": "Playgrounds",
        "description": ("Private pilot collaboration playground: small agent "
                        "teams coordinate on shared goals with verified "
                        "outcomes and non-cash credits."),
        "version": "0.2.0",
        "protocol": "playgrounds-jsonrpc/0.2",
        "a2a_compliant": False,
        "protocolBinding": "JSONRPC",
        "maxAgents": world.MAX_REGISTERED,
        "maxClassroomAgents": world.CLASSROOM_CAP,
        "registeredAgents": len(state["agents"]),
        "capabilities": {"streaming": True, "topologies": ["solo", "sealed_scouts",
                                                          "specialist_dag"]},
        "defaultInputModes": ["text", "data"],
        "defaultOutputModes": ["text", "data", "file"],
    }


# --------------------------------------------- learned routing (shadow) ---

def _routing_history(agent_id):
    return [e for e in state["routing_log"] if e.get("agent_id") == agent_id]


def learned_scores(task):
    """Interpretable outcome-trained scorer. Runs in SHADOW mode: it returns
    rankings beside the heuristic, but never assigns. Promotion requires the
    plan's held-out gate (>=100 verified tasks); until then this is evidence
    collection, not control."""
    req = task.get("required_capabilities", []) or []
    task_value = float(task.get("bounty", 10) or 10)
    ranked = []
    for a in state["agents"].values():
        hist = _routing_history(a["id"])
        n = len(hist)
        verified = sum(1 for h in hist if h.get("outcome") == "verified")
        p_accept = (verified + 1) / (n + 2)  # Laplace
        q = (sum(h.get("quality", 0.5) for h in hist) / n) if n else 0.5
        avg_cost = (sum(h.get("credits", 0) for h in hist) / n) if n else task_value * 0.5
        avg_lat = (sum(h.get("latency_s", 60) for h in hist) / n) if n else 60.0
        caps = a.get("capabilities", []) or []
        overlap = (len(set(req) & set(caps)) / len(req)) if req else 1.0
        expected_utility = (p_accept * q * overlap * task_value
                            - 0.5 * avg_cost - 0.02 * avg_lat)
        uncertainty = 1.0 / math.sqrt(n + 1)
        ranked.append({"agent_id": a["id"], "name": a.get("name"),
                       "expected_utility": round(expected_utility, 2),
                       "p_accept": round(p_accept, 3),
                       "mean_quality": round(q, 3),
                       "avg_cost": round(avg_cost, 2),
                       "avg_latency_s": round(avg_lat, 1),
                       "uncertainty": round(uncertainty, 3),
                       "samples": n})
    ranked.sort(key=lambda r: -r["expected_utility"])
    return {"mode": "shadow",
            "promoted": False,
            "gate": ("learned routing controls assignments only after >=100 "
                     "verified tasks and a held-out win vs the heuristic"),
            "learned": ranked,
            "heuristic": suggest_agents(task)}


def log_routing_outcome(task, agent_id, outcome, quality, confidence,
                        latency_s, credits):
    with lock:
        state["routing_log"].append({
            "task_id": task["id"], "agent_id": agent_id,
            "skills": task.get("required_capabilities", []) or [],
            "task_type": task.get("task_type", "general"),
            "effort": task.get("effort", 3),
            "outcome": outcome, "quality": quality, "confidence": confidence,
            "latency_s": latency_s, "credits": credits, "ts": utcnow()})
        state["routing_log"] = state["routing_log"][-ROUTING_LOG_CAP:]
        save_state()


# ------------------------------------------- reputation (deadbanded) ------
# Capability-specific Beta(2,2) posteriors. Updates happen ONLY outside the
# deadband: high-confidence clear signal moves the score; ambiguous or
# low-confidence outcomes are recorded but leave reputation untouched.

DEADBAND_HIGH_Q, DEADBAND_HIGH_C = 0.75, 0.75
DEADBAND_LOW_Q = 0.35


def beta_mean(alpha, beta):
    return alpha / (alpha + beta)


def beta_interval(alpha, beta):
    # Normal approximation to the Beta posterior interval.
    m = beta_mean(alpha, beta)
    var = alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1))
    half = 1.96 * math.sqrt(var)
    return [round(max(0.0, m - half), 3), round(min(1.0, m + half), 3)]


def get_reputation(agent_id):
    return state["reputation"].get(agent_id, {})


def update_reputation(agent_id, skills, quality, confidence):
    """Deadbanded update. Returns the list of skills whose posterior moved."""
    skills = skills or ["general"]
    moved = []
    w = clamp01(confidence, 0.0)
    with lock:
        rep = state["reputation"].setdefault(agent_id, {})
        for s in skills:
            post = rep.setdefault(s, {"alpha": 2.0, "beta": 2.0, "n": 0,
                                      "neutral": 0, "last_update": 0})
            if quality >= DEADBAND_HIGH_Q and confidence >= DEADBAND_HIGH_C:
                post["alpha"] += w
                post["n"] += 1
                post["last_update"] = utcnow()
                moved.append(s)
            elif quality <= DEADBAND_LOW_Q and confidence >= DEADBAND_HIGH_C:
                post["beta"] += w
                post["n"] += 1
                post["last_update"] = utcnow()
                moved.append(s)
            else:
                post["neutral"] = post.get("neutral", 0) + 1  # recorded only
        save_state()
    if moved:
        ledger_append("reputation_updated",
                      {"skills": moved, "quality": quality,
                       "confidence": confidence},
                      actor="orchestrator", task_id=None)
        emit("reputation_updated", {"agent_id": agent_id, "skills": moved})
    return moved


def reputation_view(agent_id):
    out = {}
    for skill, post in get_reputation(agent_id).items():
        a, b = post["alpha"], post["beta"]
        out[skill] = {"mean": round(beta_mean(a, b), 3),
                      "interval": beta_interval(a, b),
                      "directional_updates": post["n"],
                      "neutral_recorded": post.get("neutral", 0),
                      "last_update": post["last_update"]}
    return out


# ------------------------------------------------------- artifacts --------

def publish_artifact(task_id, agent_id, kind, name, content, media_type,
                     idempotency_key=None):
    dup = check_idempotency(idempotency_key) if idempotency_key else None
    if dup:
        return dup
    if not isinstance(content, str) or len(content.encode()) > 20000:
        return {"error": "artifact content must be text of at most 20000 UTF-8 bytes", "code": 400}
    raw = content.encode()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    with lock:
        if task_id not in state["tasks"]:
            return {"error": "unknown task"}
        if agent_id not in state["agents"]:
            return {"error": "unknown agent"}
        if state["tasks"][task_id]["status"] != "claimed":
            return {"error": "artifacts require an active claimed task", "code": 409}
        if agent_id != state["tasks"][task_id].get("agent_id"):
            return {"error": "only the claim holder may publish artifacts", "code": 403}
        aid = new_id("artifact")
        art = {"id": aid, "task_id": task_id, "agent_id": agent_id,
               "kind": kind or "result", "name": name or "artifact",
               "digest": digest, "size": len(raw),
               "media_type": media_type or "text/plain",
               "provenance": {"producer": agent_id, "at": utcnow()},
               "content": content,
               "created_at": utcnow()}
        state["artifacts"][aid] = art
        t = state["tasks"][task_id]
        t["artifact_ids"].append(aid)
        t["task_version"] = t.get("task_version", 1) + 1
        ledger_append("artifact_published",
                      {"artifact_id": aid, "digest": digest, "kind": art["kind"],
                       "size": art["size"]},
                      actor=agent_id, goal_id=t["goal_id"], task_id=task_id,
                      idempotency_key=idempotency_key,
                      prior_version=t["task_version"] - 1)
        save_state()
    emit("artifact_published", {"task_id": task_id, "artifact_id": aid,
                                "digest": digest})
    result = {"artifact": art}
    record_idempotency(idempotency_key, result)
    return result


def artifact_text(aid):
    a = state["artifacts"].get(aid, {})
    return a.get("content") or ""


def jaccard(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# -------------------------------------- verification + settlement --------

def run_deterministic_checks(task):
    """Executable checks first, judgment second. Returns [{id, result, detail}]."""
    checks = []
    checks.append({"id": "result_present",
                   "result": "pass" if task.get("result") else "fail",
                   "blocking": True,
                   "detail": "completion submitted a result string"})
    # artifact integrity: digests recompute
    ok = True
    for aid in task.get("artifact_ids", []):
        art = state["artifacts"].get(aid)
        if not art:
            ok = False
            break
        raw = (art.get("content") or "").encode()
        if "sha256:" + hashlib.sha256(raw).hexdigest() != art.get("digest"):
            ok = False
            break
    checks.append({"id": "artifact_integrity",
                   "result": "pass" if ok else "fail",
                   "blocking": True,
                   "detail": f"{len(task.get('artifact_ids', []))} artifacts re-hashed"})
    # duplicate / near-duplicate detection across this task's artifacts
    dup = False
    texts = [(aid, artifact_text(aid)) for aid in task.get("artifact_ids", [])]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if texts[i][1] and jaccard(texts[i][1], texts[j][1]) > 0.85:
                dup = True
    checks.append({"id": "duplicate_artifacts",
                   "result": "fail" if dup else "pass",
                   "blocking": False,
                   "detail": "near-duplicate artifacts found" if dup
                   else "no near-duplicates"})
    # output contract fields present
    contract = task.get("output_contract") or {}
    required = contract.get("required_fields", [])
    missing = [f for f in required if f not in (task.get("result") or "")]
    checks.append({"id": "contract_fields",
                   "result": "pass" if not missing else "fail",
                   "blocking": False,
                   "detail": f"missing: {missing}" if missing else "all required fields present"})
    return checks


def marginal_shares(task, artifact_scores):
    """Score-weighted pilot allocation, NOT measured counterfactual utility.
    Duplicate discounting and causal contribution evaluation are not implemented.
    """
    contributors = []
    for aid in task.get("artifact_ids", []):
        art = state["artifacts"].get(aid)
        if art and art["agent_id"] not in contributors:
            contributors.append(art["agent_id"])
    if not contributors:
        if task.get("agent_id"):
            contributors = [task["agent_id"]]
        else:
            return []
    if len(contributors) == 1:
        return [{"agent_id": contributors[0], "marginal": 1.0}]
    # value of the full set vs each hold-one-out set
    def value(agent_subset):
        total = 0.0
        for aid in task.get("artifact_ids", []):
            art = state["artifacts"].get(aid)
            if art and art["agent_id"] in agent_subset:
                total += artifact_scores.get(aid, 1.0)
        return total
    v_all = value(set(contributors))
    deltas = {}
    for c in contributors:
        rest = set(contributors) - {c}
        deltas[c] = max(0.0, value(set(contributors)) - value(rest))
    total = sum(deltas.values()) or 1.0
    return [{"agent_id": c, "marginal": deltas[c] / total}
            for c in contributors]


def verify_task(task_id, approved, approved_credits=None, verifier_agent_id=None,
                quality=0.5, confidence=0.5, rubric=None, checks=None,
                artifact_scores=None, idempotency_key=None):
    # An absent identity must never become an implicit human approval,
    # including replays from older persisted idempotency records.
    if not isinstance(verifier_agent_id, str) or not verifier_agent_id.strip():
        return {"error": "explicit verifier_agent_id required; human review is unavailable", "code": 400}
    dup = check_idempotency(idempotency_key) if idempotency_key else None
    if dup:
        return dup
    with lock:
        task = state["tasks"].get(task_id)
        if not task:
            return {"error": "unknown task", "code": 404}
        if task["status"] != "pending_verification":
            return {"error": "task not awaiting verification", "code": 409}
        if not isinstance(approved, bool):
            return {"error": "approved must be boolean", "code": 400}
        if approved_credits is not None:
            try:
                credit_amount(approved_credits)
            except ValueError as e:
                return {"error": str(e), "code": 400}
        contributors = {state["artifacts"][a]["agent_id"] for a in task.get("artifact_ids", [])
                        if a in state["artifacts"]} | {task.get("agent_id")}
        if verifier_agent_id and verifier_agent_id not in state["agents"]:
            return {"error": "unknown verifier", "code": 404}
        if verifier_agent_id and verifier_agent_id in contributors:
            return {"error": "contributors cannot verify their own work", "code": 403}
        if artifact_scores is not None:
            if not isinstance(artifact_scores, dict) or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or
                    not math.isfinite(v) or v < 0 for v in artifact_scores.values()):
                return {"error": "artifact scores must be finite non-negative numbers", "code": 400}
        goal = state["goals"].get(task["goal_id"], {})
        escrow = task.get("escrow", 0)
        worker_id = task.get("agent_id")
        approved = bool(approved)
        quality = clamp01(quality, 0.5)
        confidence = clamp01(confidence, 0.5)

        det_checks = run_deterministic_checks(task)
        if checks:
            det_checks.extend(checks)
        blocking_failed = any(c["result"] == "fail" and c.get("blocking")
                              for c in det_checks)
        # Legacy v0.1 verification shape (approved_credits, no v0.2 signals):
        # v0.1 had no deterministic gate and paid the worker in full.
        legacy = (approved_credits is not None and checks is None
                  and artifact_scores is None)
        if blocking_failed:
            approved = False

        verifier = {"type": "agent", "id": verifier_agent_id}

        receipt = {
            "verification_id": new_id("ver"),
            "task_id": task_id,
            "task_version": task.get("task_version", 1),
            "artifact_digests": [state["artifacts"][a]["digest"]
                                 for a in task.get("artifact_ids", [])
                                 if a in state["artifacts"]],
            "deterministic_checks": det_checks,
            "rubric": rubric or {},
            "decision": "accepted" if approved else "rejected",
            "confidence": confidence,
            "verifier": verifier,
            "contribution_scores": [],
            "issued_at": utcnow(),
        }
        task["verification_receipt"] = receipt
        task["verified_at"] = utcnow()

        st = state["agent_stats"].setdefault(worker_id or "unknown",
                                             blank_agent_stats())
        latency = max(0.0, (task.get("completed_at") or utcnow())
                      - (task.get("claimed_at") or utcnow()))

        if approved:
            task["status"] = "done"
            paid_total = approved_credits if approved_credits is not None else escrow
            paid_total = max(0, min(paid_total, escrow))
            # Legacy v0.1 verifications pay the worker the full approved
            # amount (no review pool); the 90/10 split is v0.2-only.
            review_pct = 0.0 if legacy else float(
                goal.get("review_pool_pct", 0.10) or 0.0)
            work_pool = round(paid_total * (1 - review_pct), 2)
            review_pool = round(paid_total - work_pool, 2)
            leftover = round(escrow - paid_total, 2)

            shares = marginal_shares(task, artifact_scores or {})
            receipt["contribution_scores"] = shares
            # Largest-remainder allocation in integer cents conserves the pool exactly.
            cents = int(round(work_pool * 100))
            weights = [max(0, x["marginal"]) for x in shares]
            total_weight = sum(weights)
            raw_cents = [cents * w / total_weight if total_weight else 0 for w in weights]
            allocations = [math.floor(x) for x in raw_cents]
            if total_weight:
                order = sorted(range(len(shares)), key=lambda i: (-(raw_cents[i] - allocations[i]), shares[i]["agent_id"]))
                for i in order[:cents - sum(allocations)]:
                    allocations[i] += 1
            payouts = {}
            for share, count in zip(shares, allocations):
                aid = share["agent_id"]
                ag = state["agents"].get(aid)
                if ag:
                    amt = count / 100
                    ag["credits"] = round(ag.get("credits", 0) + amt, 2)
                    payouts[aid] = amt
                    contributor_stats = state["agent_stats"].setdefault(aid, blank_agent_stats())
                    contributor_stats["credits_earned"] = round(contributor_stats["credits_earned"] + amt, 2)
            leftover = round(leftover + work_pool - sum(payouts.values()), 2)
            # review/integration pool: only to an eligible independent reviewer
            reviewer_paid = 0.0
            if (review_pool > 0 and verifier_agent_id
                    and verifier_agent_id != worker_id
                    and verifier_agent_id in state["agents"]):
                ra = state["agents"][verifier_agent_id]
                ra["credits"] = round(ra.get("credits", 0) + review_pool, 2)
                rst = state["agent_stats"].setdefault(verifier_agent_id,
                                                      blank_agent_stats())
                rst["review_credits_earned"] += review_pool
                reviewer_paid = review_pool
            else:
                leftover = round(leftover + review_pool, 2)

            goal["budget_available"] = round(
                goal.get("budget_available", 0) + leftover, 2)
            goal["budget_spent"] = round(
                goal.get("budget_spent", 0) + sum(payouts.values()) + reviewer_paid, 2)
            st["verified"] += 1

            settlement = {
                "settlement_id": new_id("settle"),
                "task_id": task_id, "escrow": escrow,
                "approved_total": paid_total, "work_pool": work_pool,
                "review_pool": review_pool, "reviewer_paid": reviewer_paid,
                "leftover_to_budget": leftover, "payouts": payouts,
                "shares": shares,
                "rationale": ("score-weighted pilot split of the work pool; "
                              "review pool to independent verifier or budget"),
                "issued_at": utcnow(),
            }
            task["settlement_receipt"] = settlement
            ledger_append("credits_settled", settlement, actor="orchestrator",
                          goal_id=task["goal_id"], task_id=task_id,
                          idempotency_key=idempotency_key)
            outcome, q = "verified", quality
        else:
            task["status"] = "open"
            task["agent_id"] = None
            task["result"] = None
            task["rejections"] = task.get("rejections", 0) + 1
            goal["budget_available"] = round(
                goal.get("budget_available", 0) + escrow, 2)
            st["rejected"] += 1
            outcome, q = "rejected", quality

        receipt["signature"] = "stub:" + hashlib.sha256(
            (json.dumps(receipt, sort_keys=True) + state.get("server_salt", "")).encode()).hexdigest()[:32]
        task["escrow"] = 0
        task["claim_expires"] = 0
        task["lease"] = {"holder": None, "expires": 0, "last_progress_at": 0}
        task["task_version"] = task.get("task_version", 1) + 1

        # observed profile: claims stay Playgrounds-owned history
        if worker_id and worker_id in state["agents"]:
            obs = state["agents"][worker_id].setdefault("observed", {})
            obs["tasks"] = obs.get("tasks", 0) + 1
            obs["latency_sum"] = obs.get("latency_sum", 0.0) + latency
            obs["cost_sum"] = obs.get("cost_sum", 0.0) + (paid_total if approved else 0)
            if approved:
                obs["verified"] = obs.get("verified", 0) + 1
                obs["quality_sum"] = obs.get("quality_sum", 0.0) + quality

        log_routing_outcome(task, worker_id, outcome, q, confidence,
                            latency, paid_total if approved else 0)
        ledger_append("verification_issued",
                      {"verification_id": receipt["verification_id"],
                       "decision": receipt["decision"],
                       "confidence": confidence,
                       "checks": [(c["id"], c["result"]) for c in det_checks]},
                      actor=verifier["id"], goal_id=task["goal_id"],
                      task_id=task_id, idempotency_key=idempotency_key,
                      prior_version=receipt["task_version"])
        save_state()

    # deadbanded reputation lives outside the lock (takes it itself).
    # quality always describes the assessed work quality; a rejection with
    # low quality is a negative signal, not an inverted one.
    if worker_id:
        update_reputation(worker_id,
                          task.get("required_capabilities") or ["general"],
                          quality, confidence)
    emit("task_verified", {"task_id": task_id, "approved": approved,
                           "status": task["status"],
                           "paid": paid_total if approved else 0,
                           "verification_id": receipt["verification_id"]})
    result = {"task": task, "verification_receipt": receipt,
              "settlement_receipt": task.get("settlement_receipt")}
    record_idempotency(idempotency_key, result)
    return result

# --------------------------------- heuristic delegation (cold-start) ------
# v0.1 logic preserved verbatim: this is the cold-start prior. The learned
# router (shadow mode) trains against its outcomes; static tiers never become
# reputation or routing evidence on their own.

def suggest_agents(task):
    """Rank agents for a task the way a thoughtful human delegator would:
    skill fit first, then whether the agent's model is right-sized for the
    task's effort, then track record, availability, and cost."""
    req = task.get("required_capabilities", []) or []
    effort = clamp_effort(task.get("effort", 3))
    suggestions = []
    for a in state["agents"].values():
        caps = a.get("capabilities", []) or []
        cap_match = (len(set(req) & set(caps)) / len(req)) if req else 1.0

        tier = a.get("model_tier", 3)
        gap = tier - effort
        if gap >= 0:
            model_fit = max(0.3, 1.0 - 0.15 * gap)
            model_note = ("model is stronger than this task needs"
                          if gap >= 2 else "model fits this task well")
        else:
            model_fit = max(0.1, 1.0 - 0.35 * (-gap))
            model_note = "model may be underpowered for this effort level"

        st = state["agent_stats"].get(a["id"], {})
        v, r = st.get("verified", 0), st.get("rejected", 0)
        reliability = (v + 1) / (v + r + 2)
        track_note = (f"{v} verified, {r} rejected" if (v + r)
                      else "new agent — no track record yet")

        available = a.get("status") == "idle"
        avail_score = 1.0 if available else 0.2

        cost_factor = 1.0 / (1.0 + 0.1 * (tier - 1))
        base = (0.35 * cap_match + 0.25 * model_fit
                + 0.25 * reliability + 0.15 * avail_score)
        score = round(base * cost_factor * 100, 1)

        reasons = [
            f"capability match {int(cap_match * 100)}%"
            + ("" if req else " (task lists no required capabilities)"),
            f"model '{a.get('model', 'unknown')}' (tier {tier}) vs effort {effort}: {model_note}",
            f"track record: {track_note}",
            "idle and available now" if available else "currently busy on another task",
        ]
        suggestions.append({"agent_id": a["id"], "name": a.get("name"),
                            "score": score, "reasons": reasons,
                            "breakdown": {"capability": round(cap_match, 2),
                                          "model_fit": round(model_fit, 2),
                                          "reliability": round(reliability, 2),
                                          "availability": avail_score,
                                          "cost_factor": round(cost_factor, 2)}})
    suggestions.sort(key=lambda s: -s["score"])
    return suggestions


def latest_topology_decision(task_id):
    cands = [d for d in state["decisions"].values()
             if d.get("kind") == "topology" and d.get("task_id") == task_id]
    return max(cands, key=lambda d: d["ts"]) if cands else None


def create_task(goal_id, body, actor="human"):
    if actor == "human" and _active_caller:
        actor = _active_caller
    """Shared task-creation command used by REST and A2A. Returns
    (task_dict, error_dict)."""
    with lock:
        if goal_id not in state["goals"]:
            return None, {"error": "unknown goal", "code": 404}
        try:
            credit_amount(body.get("bounty", 10))
        except ValueError as e:
            return None, {"error": str(e), "code": 400}
        dependencies = body.get("dependencies", [])
        if not isinstance(dependencies, list) or any(not isinstance(d, str) or
                d not in state["tasks"] or state["tasks"][d]["goal_id"] != goal_id for d in dependencies):
            return None, {"error": "dependencies must reference existing tasks in this goal", "code": 400}
        tid = new_id("task")
        plan_id = body.get("plan_id")
        if plan_id and (plan_id not in state["plans"] or state["plans"][plan_id]["goal_id"] != goal_id):
            return None, {"error": "plan must belong to this goal", "code": 400}
        task = {
            "id": tid, "goal_id": goal_id, "plan_id": plan_id,
            "title": body.get("title", "Untitled task"),
            "status": "open", "agent_id": None, "result": None,
            "bounty": body.get("bounty", 10),
            "required_capabilities": body.get("required_capabilities", []),
            "effort": clamp_effort(body.get("effort", 3)),
            "task_type": body.get("task_type", "general"),
            "dependencies": body.get("dependencies", []),
            "success_criteria": body.get("success_criteria", ""),
            "risk": (body.get("risk") or "medium").lower(),
            "decomposability": clamp01(body.get("decomposability", 0.3), 0.3),
            "coupling": clamp01(body.get("coupling", 0.7), 0.7),
            "input_contract": body.get("input_contract", {}),
            "output_contract": body.get("output_contract", {}),
            "topology": "solo", "task_version": 1,
            "artifact_ids": [], "progress": [],
            "lease": {"holder": None, "expires": 0, "last_progress_at": 0},
            "stall_count": 0,
            "verification_receipt": None, "settlement_receipt": None,
            "escrow": 0, "rejections": 0,
            "created_at": utcnow(), "claimed_at": None,
            "claim_expires": 0, "completed_at": None, "verified_at": None,
        }
        state["tasks"][tid] = task
        if plan_id and plan_id in state["plans"]:
            state["plans"][plan_id]["task_ids"].append(tid)
        ledger_append("task_created",
                      {"title": task["title"], "bounty": task["bounty"],
                       "task_version": 1},
                      actor=actor, goal_id=goal_id, task_id=tid)
        save_state()
    emit("task_created", {"task": {k: task[k] for k in
                                   ("id", "title", "status", "bounty")}})
    orch = orchestrate_task(task)
    with lock:
        task = state["tasks"].get(tid, task)
    task = dict(task)
    task["orchestration"] = orch
    return task, None


class Handler(BaseHTTPRequestHandler):
    server_version = "Playgrounds/0.2"

    def log_message(self, *a):
        pass

    def _send(self, code, obj, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n < 0 or n > 262144:
            raise ValueError("request body limit is 256 KiB")
        if not n:
            return {}
        return json.loads(self.rfile.read(n) or b"{}", parse_constant=lambda v: (_ for _ in ()).throw(ValueError("non-finite JSON number")))

    def _allowed_host(self):
        host = (urlparse("http://" + self.headers.get("Host", "")).hostname
                or "").lower()
        return host in ("localhost", "127.0.0.1", "::1") or host in ALLOWED_HOSTS

    def _operator_ok(self):
        """Public-mode gate. When PLAYGROUNDS_OPERATOR_TOKEN is unset everything
        stays open (loopback pilot). When set, the lobby API, the room
        directory and room creation require it as an Authorization: Bearer
        header. Credentials never travel in URLs: query tokens are not
        accepted. Invite joins and room bearer calls are unaffected."""
        want = os.environ.get("PLAYGROUNDS_OPERATOR_TOKEN", "")
        if not want:
            return True
        auth = self.headers.get("Authorization", "")
        return (auth.startswith("Bearer ")
                and hmac.compare_digest(auth[len("Bearer "):].strip(), want))

    def _origin_ok(self):
        """Same-origin writes are allowed over http and https. Anything else
        must match the explicitly configured PLAYGROUNDS_TRUSTED_ORIGIN
        verbatim — never a forwarded header."""
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        if origin == "http://" + host or origin == "https://" + host:
            return True
        return bool(TRUSTED_ORIGIN) and origin == TRUSTED_ORIGIN

    def do_POST(self):
        if not self._allowed_host():
            return self._send(403, {"error": "loopback Host required"})
        if not self._origin_ok():
            return self._send(403, {"error": "cross-origin writes forbidden"})
        try:
            if self.headers.get_content_type() != "application/json":
                return self._send(415, {"error": "application/json required"})
            body = self._body()
            if not isinstance(body, dict):
                raise ValueError("JSON object required")
            for field in ("budget", "bounty", "approved_credits"):
                if field in body and body[field] is not None:
                    credit_amount(body[field])
            if "review_pool_pct" in body:
                v = body["review_pool_pct"]
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
                    raise ValueError("review_pool_pct must be between 0 and 1")
            # Scope retry keys to operation and exact payload; never replay another task's response.
            key = body.get("idempotency_key")
            if key:
                if not isinstance(key, str) or len(key) > 256:
                    raise ValueError("invalid idempotency key")
                body["idempotency_key"] = hashlib.sha256(
                    (self.path + json.dumps(body, sort_keys=True)).encode()).hexdigest()
            self._request_body = body
            with lock:
                sweep_expired_claims()
                self._post()
        except (ValueError, TypeError, UnicodeError) as e:
            return self._send(400, {"error": str(e)})

    # ---------- GET ----------
    def do_GET(self):
        if not self._allowed_host():
            return self._send(403, {"error": "loopback Host required"})
        if self._room_route_get():
            return
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        # The dashboard shell is static and carries no secrets: invited
        # non-operators must be able to open the join UI without an operator
        # key. Static assets are likewise public. Everything data-bearing
        # stays behind the operator gate.
        public_asset = (parsed.path == "/"
                        or parsed.path.startswith("/avatars/")
                        or parsed.path.startswith("/assets/"))
        if not public_asset and not self._operator_ok():
            return self._send(403, {"error": "operator token required"})
        self._dispatch_get(parts, parsed)

    def _dispatch_get(self, parts, parsed):
            if parsed.path == "/":
                with open(DASHBOARD_PATH, "rb") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            elif parsed.path == "/.well-known/agent-card.json":
                with lock:
                    self._send(200, playground_card())
            elif len(parts) == 2 and parts[0] == "avatars" and parts[1] in (
                    "plush1.png", "plush2.png", "plush3.png", "plush4.png"):
                fp = os.path.join(AVATAR_DIR, parts[1])
                if not os.path.exists(fp):
                    return self._send(404, {"error": "avatar not found"})
                with open(fp, "rb") as f:
                    self._send(200, f.read(), "image/png")
            elif parsed.path in ("/assets/campus.js", "/assets/campus-layout.js",
                                 "/assets/campus-navigation.js", "/assets/campus-interactions.js",
                                 "/assets/campus-animation.js", "/assets/vendor/three-pathfinding.module.js",
                                 "/assets/vendor/three.module.js", "/assets/vendor/three.core.js"):
                # Exact allowlist, never an arbitrary filesystem/static-file route.
                with open(os.path.join(ROOT, parsed.path.lstrip("/")), "rb") as f:
                    self._send(200, f.read(), "text/javascript; charset=utf-8")
            elif parsed.path == "/api/state":
                with lock:
                    self._send(200, _public_lobby_state_locked())
            elif parsed.path == "/api/world":
                with lock:
                    self._send(200, world.snapshot(state))
            elif parsed.path == "/api/policy":
                with lock:
                    self._send(200, state["policy"])
            elif parsed.path == "/api/ledger":
                qs = parse_qs(parsed.query)
                since = int(qs.get("since", [0])[0])
                gid = qs.get("goal_id", [None])[0]
                typ = qs.get("type", [None])[0]
                with lock:
                    evs = [e for e in state["ledger"]
                           if e["seq"] > since
                           and (gid is None or e.get("goal_id") == gid)
                           and (typ is None or e.get("type") == typ)]
                    self._send(200, {"events": evs[-500:], "digest": ledger_digest(),
                                     "ledger_seq": state["ledger_seq"]})
            elif parsed.path == "/api/events":
                qs = parse_qs(parsed.query)
                since = int(qs.get("since", [0])[0])
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                sub = queue.Queue(maxsize=256)
                try:
                    with lock:
                        replay = [ev for ev in state["events"] if ev["seq"] > since]
                        subscribers[sub] = None
                        sse_owner[sub] = None
                    self.connection.settimeout(20)
                    for ev in replay:
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                    self.wfile.flush()
                    while True:
                        try:
                            payload = sub.get(timeout=15)
                        except queue.Empty:
                            with lock:
                                if sub not in subscribers:
                                    # Evicted (queue-full or revoked): the
                                    # handler sends "Connection: keep-alive",
                                    # which flips close_connection off in
                                    # CPython's send_header. Force the socket
                                    # closed so the client gets EOF and
                                    # reconnects for current state.
                                    self.close_connection = True
                                    break
                            payload = b": ping\n\n"
                        self.wfile.write(payload)
                        self.wfile.flush()
                except (OSError, TimeoutError):
                    pass
                finally:
                    with lock:
                        subscribers.pop(sub, None)
                        sse_owner.pop(sub, None)
            elif parsed.path == "/api/messages":
                qs = parse_qs(parsed.query)
                since = int(qs.get("since", [0])[0])
                gid = qs.get("goal_id", [None])[0]
                with lock:
                    msgs = [m for m in state["messages"]
                            if m["seq"] > since and (gid is None or m.get("goal_id") == gid)]
                    self._send(200, {"messages": msgs[-100:]})
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "tasks" \
                    and parts[3] == "suggest":
                tid = parts[2]
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        self._send(404, {"error": "unknown task"})
                    else:
                        self._send(200, {"task_id": tid,
                                         "suggestions": suggest_agents(task)})
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "tasks" \
                    and parts[3] == "route":
                tid = parts[2]
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        self._send(404, {"error": "unknown task"})
                    else:
                        self._send(200, {"task_id": tid,
                                         "routing": learned_scores(task)})
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "tasks" \
                    and parts[3] == "topology":
                tid = parts[2]
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        self._send(404, {"error": "unknown task"})
                    else:
                        self._send(200, {"task_id": tid,
                                         "topology": task.get("topology", "solo"),
                                         "decision": latest_topology_decision(tid)})
            elif len(parts) == 3 and parts[0] == "api" and parts[1] == "decisions":
                did = parts[2]
                with lock:
                    d = state["decisions"].get(did)
                    if not d:
                        self._send(404, {"error": "unknown decision"})
                    else:
                        self._send(200, d)
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "agents" \
                    and parts[3] == "stats":
                aid = parts[2]
                with lock:
                    agent = state["agents"].get(aid)
                    if not agent:
                        self._send(404, {"error": "unknown agent"})
                    else:
                        st = state["agent_stats"].get(aid, blank_agent_stats())
                        denom = st["verified"] + st["rejected"]
                        success = (st["verified"] / denom) if denom else None
                        avg = (st["work_seconds"] / st["completed"]) if st["completed"] else None
                        self._send(200, {
                            "agent": agent,
                            "tasks_submitted": st["completed"],
                            "tasks_verified": st["verified"],
                            "tasks_rejected": st["rejected"],
                            "success_rate": success,
                            "avg_task_seconds": avg,
                            "credits_earned": st["credits_earned"],
                            "review_credits_earned": st.get("review_credits_earned", 0),
                            "credits_balance": agent.get("credits", 0),
                            "model": agent.get("model", "unknown"),
                            "model_tier": agent.get("model_tier", 3),
                        })
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "agents" \
                    and parts[3] == "card":
                aid = parts[2]
                with lock:
                    agent = state["agents"].get(aid)
                    if not agent:
                        self._send(404, {"error": "unknown agent"})
                    else:
                        self._send(200, build_agent_card(agent))
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "agents" \
                    and parts[3] == "reputation":
                aid = parts[2]
                with lock:
                    if aid not in state["agents"]:
                        self._send(404, {"error": "unknown agent"})
                    else:
                        self._send(200, {"agent_id": aid,
                                         "reputation": reputation_view(aid)})
            elif len(parts) == 4 and parts[0] == "api" and parts[1] == "goals" \
                    and parts[3] == "context":
                gid = parts[2]
                with lock:
                    ns = state["context"].get(gid, {})
                    self._send(200, {"goal_id": gid, "context": ns})
            else:
                self._send(404, {"error": "not found"})

# ---------- POST ----------
    def _post(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        body = self._request_body
        if self._room_route_post(parts, body):
            return
        if not self._operator_ok():
            self._send(403, {"error": "operator token required"})
            return
        self._dispatch_post(parts, body)

    def _dispatch_post(self, parts, body):
            if len(parts) == 4 and parts[:2] == ["api", "agents"] and parts[3] == "presence":
                res = world.move(state, parts[2], body)
                if res.get("error"):
                    return self._send(res["code"], res)
                emit("presence_changed", {"agent_id": parts[2], **res})
                return self._send(200, res)

            if parts == ["api", "social"]:
                res = world.post_social(state, body, utcnow())
                if res.get("error"):
                    return self._send(res["code"], res)
                emit("social_posted", {"agent_id": body["agent_id"], "seq": res["message"]["seq"]})
                return self._send(200, res)

            if parts == ["api", "agents", "register"]:
                with lock:
                    space = body.get("space", "classroom")  # legacy connectors retain their lobby
                    if space not in ("classroom", "playground"):
                        return self._send(400, {"error": "invalid space"})
                    if "social_enabled" in body and not isinstance(body["social_enabled"], bool):
                        return self._send(400, {"error": "social_enabled must be boolean"})
                    if len(state["agents"]) >= world.MAX_REGISTERED:
                        return self._send(409, {"error": "pilot registration limit reached"})
                    if space == "classroom" and not world.classroom_available(state, None, None):
                        return self._send(409, {"error": "classroom is full",
                                                "max_agents": world.CLASSROOM_CAP})
                    aid = new_id("agent")
                    slot = len(state["agents"])  # 0-based plush slot
                    agent = build_agent_record(body, aid, slot,
                                             body.get("tenant_id", "local"),
                                             space)
                    state["agents"][aid] = agent
                    ledger_append("agent_registered",
                                  {"name": agent["name"], "plush": agent["plush"],
                                   "skills": [s.get("id") for s in
                                              agent["agent_card"]["skills"]] or
                                  agent["capabilities"]},
                                  actor=aid)
                    save_state()
                emit("agent_registered", {"agent": agent})
                return self._send(200, {"id": aid, "agent": agent,
                                        "card": build_agent_card(agent)})

            if len(parts) == 4 and parts[:2] == ["api", "agents"] and parts[3] == "heartbeat":
                aid = parts[2]
                sweep_expired_claims()
                detect_stalls()
                with lock:
                    agent = state["agents"].get(aid)
                    if not agent:
                        return self._send(404, {"error": "unknown agent"})
                    agent["status"] = body.get("status", agent["status"])
                    if "current_task" in body:
                        agent["current_task"] = body["current_task"]
                    agent["last_heartbeat"] = utcnow()
                    save_state()
                emit("agent_heartbeat", {"agent_id": aid, "status": agent["status"],
                                        "current_task": agent["current_task"]})
                return self._send(200, {"ok": True})

            if parts == ["api", "goals"]:
                with lock:
                    gid = new_id("goal")
                    budget = body.get("budget", 1000)
                    goal = {"id": gid, "title": body.get("title", "Untitled goal"),
                            "description": body.get("description", ""),
                            "budget": budget, "budget_available": budget,
                            "budget_spent": 0,
                            "tenant_id": body.get("tenant_id", "local"),
                            "review_pool_pct": float(body.get("review_pool_pct", 0.10)),
                            "plan_ids": [],
                            "created_at": utcnow()}
                    state["goals"][gid] = goal
                    ledger_append("goal_created", {"title": goal["title"],
                                                  "budget": budget},
                                  actor=_active_caller or "human", goal_id=gid)
                    save_state()
                emit("goal_created", {"goal": goal})
                return self._send(200, goal)

            if len(parts) == 4 and parts[:2] == ["api", "goals"] and parts[3] == "plans":
                gid = parts[2]
                plan = create_plan(gid, body.get("objective", ""),
                                   body.get("success_criteria", ""),
                                   body.get("topology_policy", "solo_first"))
                if not plan:
                    return self._send(404, {"error": "unknown goal"})
                return self._send(200, plan)

            if len(parts) == 4 and parts[0] == "api" and parts[1] == "plans" \
                    and parts[3] == "replan":
                pid = parts[2]
                plan = replan(pid, body.get("reason", "manual replan"),
                              body.get("changes"))
                if not plan:
                    return self._send(404, {"error": "unknown plan"})
                return self._send(200, plan)

            if len(parts) == 4 and parts[:2] == ["api", "goals"] and parts[3] == "tasks":
                gid = parts[2]
                task, err = create_task(gid, body)
                if err:
                    return self._send(err.get("code", 400), err)
                return self._send(200, task)

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "clarify":
                tid = parts[2]
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        return self._send(404, {"error": "unknown task"})
                    if task["status"] != "needs_input":
                        return self._send(409, {"error": "task is not awaiting clarification"})
                    if not isinstance(body.get("success_criteria"), str) or not body["success_criteria"].strip():
                        return self._send(400, {"error": "non-empty success_criteria required"})
                    if body.get("success_criteria"):
                        task["success_criteria"] = body["success_criteria"]
                    if body.get("input_contract"):
                        task["input_contract"] = body["input_contract"]
                    task["status"] = "open"
                    task["task_version"] += 1
                    ledger_append("clarification_provided",
                                  {"success_criteria": task["success_criteria"]},
                                  actor=body.get("by", "human"),
                                  goal_id=task["goal_id"], task_id=tid,
                                  prior_version=task["task_version"] - 1)
                    save_state()
                emit("task_open", {"task_id": tid})
                decision = select_topology(state["tasks"][tid])
                with lock:
                    t = state["tasks"][tid]
                    t["topology"] = decision["output"]["topology"]
                    save_state()
                    out = dict(t)
                out["orchestration"] = decision
                return self._send(200, out)

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "claim":
                tid = parts[2]
                key = body.get("idempotency_key")
                dup = check_idempotency(key)
                if dup:
                    return self._send(200, dup)
                sweep_expired_claims()
                with lock:
                    task = state["tasks"].get(tid)
                    aid = body.get("agent_id")
                    if not task:
                        return self._send(404, {"error": "unknown task"})
                    if aid not in state["agents"]:
                        return self._send(404, {"error": "unknown agent"})
                    if task["status"] != "open":
                        return self._send(409, {"error": f"task is {task['status']}"})
                    if any(state["tasks"].get(d, {}).get("status") != "done" for d in task.get("dependencies", [])):
                        return self._send(409, {"error": "dependencies not completed"})
                    space_error = world.claim_error(state, aid, task["goal_id"])
                    if space_error:
                        return self._send(space_error["code"], space_error)
                    # A new attempt must not inherit rejected artifacts or progress.
                    task["artifact_ids"] = []
                    task["progress"] = []
                    task["stall_count"] = 0
                    task["verification_receipt"] = None
                    task["settlement_receipt"] = None
                    goal = state["goals"].get(task["goal_id"], {})
                    bounty = task.get("bounty", 10)
                    if bounty > goal.get("budget_available", 0):
                        return self._send(409, {"error": "insufficient goal budget for bounty"})
                    goal["budget_available"] = round(goal.get("budget_available", 0) - bounty, 2)
                    task["escrow"] = bounty
                    task["status"] = "claimed"
                    task["agent_id"] = aid
                    task["claimed_at"] = utcnow()
                    task["claim_expires"] = utcnow() + CLAIM_WINDOW
                    task["lease"] = {"holder": aid, "expires": task["claim_expires"],
                                     "last_progress_at": utcnow()}
                    task["task_version"] += 1
                    ledger_append("task_leased",
                                  {"agent_id": aid, "bounty": bounty, "escrow": bounty,
                                   "lease_expires": task["claim_expires"]},
                                  actor=aid, goal_id=task["goal_id"], task_id=tid,
                                  idempotency_key=key,
                                  prior_version=task["task_version"] - 1)
                    save_state()
                    out = dict(task)
                emit("task_claimed", {"task_id": tid, "agent_id": aid,
                                      "bounty": bounty, "escrow": bounty})
                record_idempotency(key, {"task": out})
                return self._send(200, {"task": out})

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "progress":
                tid = parts[2]
                key = body.get("idempotency_key")
                dup = check_idempotency(key)
                if dup:
                    return self._send(200, dup)
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        return self._send(404, {"error": "unknown task"})
                    if task["status"] != "claimed" or task["agent_id"] != body.get("agent_id"):
                        return self._send(409, {"error": "task not claimed by this agent"})
                    cp = {"at": utcnow(), "note": body.get("note", ""),
                          "progress_pct": clamp01(body.get("progress_pct", 0.0), 0.0)}
                    task["progress"].append(cp)
                    task["progress"] = task["progress"][-50:]
                    task["lease"]["last_progress_at"] = utcnow()
                    task["lease"]["expires"] = utcnow() + CLAIM_WINDOW  # progress renews lease
                    task["claim_expires"] = task["lease"]["expires"]
                    ledger_append("progress_recorded", cp, actor=body.get("agent_id"),
                                  goal_id=task["goal_id"], task_id=tid,
                                  idempotency_key=key)
                    save_state()
                    out = {"task_id": tid, "checkpoint": cp,
                           "checkpoints": len(task["progress"])}
                emit("progress_recorded", {"task_id": tid, "checkpoint": cp})
                record_idempotency(key, out)
                return self._send(200, out)

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "artifacts":
                tid = parts[2]
                res = publish_artifact(tid, body.get("agent_id"), body.get("kind"),
                                       body.get("name"), body.get("content"),
                                       body.get("media_type"),
                                       body.get("idempotency_key"))
                if res.get("error"):
                    return self._send(res.get("code", 404), res)
                return self._send(200, res)

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "complete":
                tid = parts[2]
                key = body.get("idempotency_key")
                dup = check_idempotency(key)
                if dup:
                    return self._send(200, dup)
                with lock:
                    task = state["tasks"].get(tid)
                    if not task:
                        return self._send(404, {"error": "unknown task"})
                    if task["status"] != "claimed" or task["agent_id"] != body.get("agent_id"):
                        return self._send(409, {"error": "task not claimed by this agent"})
                    task["status"] = "pending_verification"
                    task["result"] = body.get("result", "")
                    task["completed_at"] = utcnow()
                    task["task_version"] += 1
                    _st = state["agent_stats"].setdefault(body.get("agent_id"),
                                                         blank_agent_stats())
                    _st["completed"] += 1
                    if task.get("claimed_at"):
                        _st["work_seconds"] += max(0.0, task["completed_at"] - task["claimed_at"])
                    ledger_append("task_submitted",
                                  {"result_chars": len(task["result"] or "")},
                                  actor=body.get("agent_id"), goal_id=task["goal_id"],
                                  task_id=tid, idempotency_key=key,
                                  prior_version=task["task_version"] - 1)
                    save_state()
                    out = dict(task)
                emit("task_completed", {"task_id": tid, "agent_id": task["agent_id"],
                                        "result": task["result"]})
                record_idempotency(key, {"task": out})
                return self._send(200, {"task": out})

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "verify":
                tid = parts[2]
                res = verify_task(
                    tid, body.get("approved"),
                    approved_credits=body.get("approved_credits"),
                    verifier_agent_id=body.get("verifier_agent_id"),
                    quality=body.get("quality", 0.5),
                    confidence=body.get("confidence", 0.5),
                    rubric=body.get("rubric"),
                    checks=body.get("checks"),
                    artifact_scores=body.get("artifact_scores"),
                    idempotency_key=body.get("idempotency_key"))
                if res.get("error"):
                    return self._send(res.get("code", 400), res)
                return self._send(200, res)

            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "cancel":
                tid = parts[2]
                t = cancel_task(tid, by=body.get("by", "human"),
                                reason=body.get("reason", "cancelled"))
                if not t:
                    return self._send(404, {"error": "unknown or terminal task"})
                return self._send(200, {"task": t})

            if parts == ["api", "messages"]:
                frm = body.get("from_agent")
                to = body.get("to_agent")
                text = body.get("text", "")
                if not text:
                    return self._send(400, {"error": "text required"})
                with lock:
                    if frm not in state["agents"]:
                        return self._send(404, {"error": "unknown from_agent"})
                    if to and to not in state["agents"]:
                        return self._send(404, {"error": "unknown to_agent"})
                    state["msg_seq"] += 1
                    msg = {"seq": state["msg_seq"], "id": new_id("msg"),
                           "from_agent": frm, "to_agent": to,
                           "goal_id": body.get("goal_id"), "text": text,
                           "at": utcnow()}
                    state["messages"].append(msg)
                    state["messages"] = state["messages"][-500:]
                    save_state()
                emit("message_sent", {"message": msg})
                return self._send(200, msg)

            if len(parts) == 4 and parts[0] == "api" and parts[1] == "goals" \
                    and parts[3] == "context":
                gid = parts[2]
                key = body.get("key")
                if not key:
                    return self._send(400, {"error": "key required"})
                with lock:
                    ns = state["context"].setdefault(gid, {})
                    entry = ns.get(key)
                    if not entry or entry.get("kind") != "value":
                        entry = {"kind": "value", "history": []}
                    entry["value"] = body.get("value")
                    entry["updated_by"] = body.get("agent_id")
                    entry["updated_at"] = utcnow()
                    entry["history"].append({"value": body.get("value"),
                                            "by": body.get("agent_id"),
                                            "at": utcnow()})
                    entry["history"] = entry["history"][-20:]
                    ns[key] = entry
                    save_state()
                emit("context_updated", {"goal_id": gid, "key": key, "kind": "value",
                                        "by": body.get("agent_id")})
                return self._send(200, {"ok": True, "entry": entry})

            if len(parts) == 5 and parts[0] == "api" and parts[1] == "goals" \
                    and parts[3] == "context" and parts[4] == "append":
                gid = parts[2]
                key = body.get("key")
                if not key:
                    return self._send(400, {"error": "key required"})
                with lock:
                    ns = state["context"].setdefault(gid, {})
                    entry = ns.get(key)
                    if not entry or entry.get("kind") != "log":
                        entry = {"kind": "log", "log": []}
                    entry["log"].append({"entry": body.get("entry"),
                                         "by": body.get("agent_id"),
                                         "at": utcnow()})
                    entry["log"] = entry["log"][-100:]
                    ns[key] = entry
                    save_state()
                emit("context_updated", {"goal_id": gid, "key": key, "kind": "log",
                                        "by": body.get("agent_id")})
                return self._send(200, {"ok": True, "entry": entry})

            if parts == ["a2a"]:
                return self._handle_a2a(body)

            self._send(404, {"error": "not found"})

        # ---------- A2A (minimal JSON-RPC slice) ----------
    # ------------------------------------------------- rooms ---
    # Authenticated, isolated collaboration scopes. The lobby API above is
    # unchanged (localhost pilot, no auth). Every room endpoint requires a
    # bearer token except room creation (bootstrap) and invite redemption.

    def _bearer_token(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[len("Bearer "):].strip()
        return token or None

    def _room_bearer(self, room):
        """Authenticate the Authorization header against the room's credential
        map. Returns the agent id, or None. A removed member is rejected even
        if a stale auth entry survived."""
        token = self._bearer_token()
        if not token:
            return None
        agent_id = room["auth"].get(token_hash(token))
        return agent_id if agent_id in room["members"] else None

    def _room_public(self, room, caller=None):
        """Directory-safe room metadata. caller_agent_id is the
        bearer-authenticated caller (already sanitized: an agent id string)."""
        return {"id": room["id"], "name": room["name"],
                "created_at": room["created_at"],
                "owner_agent_id": room["owner_agent_id"],
                "caller_agent_id": caller,
                "members": [{"agent_id": aid,
                             "name": room["agents"].get(aid, {}).get("name", aid),
                             "role": m["role"], "joined_at": m["joined_at"]}
                            for aid, m in room["members"].items()]}

    def _room_policy(self, room):
        return {"auth_required": True, "auth_scheme": "bearer",
                "room_id": room["id"], "max_agents": ROOM_MAX_AGENTS,
                "invite_ttl_default_seconds": INVITE_DEFAULT_TTL,
                "public_join": False, "credits_are_non_cash": True,
                "note": ("Room endpoints require 'Authorization: Bearer <token>'. "
                         "Membership is invite-only; there is no public join.")}

    def _room_route_get(self):
        """Route GET /api/rooms/... . Returns True when the request was handled."""
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        if parts[:2] != ["api", "rooms"]:
            return False
        if len(parts) == 2:
            # Room directory: ids, names, member counts only. Invite tokens and
            # membership details stay behind member auth. Operator-gated in
            # public mode so strangers cannot enumerate rooms.
            if not self._operator_ok():
                self._send(403, {"error": "operator token required"})
                return True
            with lock:
                rooms = [{"id": r["id"], "name": r["name"],
                          "created_at": r["created_at"],
                          "members": len(r["members"])}
                         for r in state["rooms"].values()]
            self._send(200, {"rooms": rooms})
            return True
        rid, rest = parts[2], parts[3:]
        if rest == ["events"]:
            return self._room_sse(rid, parsed)
        with lock:
            room = state["rooms"].get(rid)
            if room is None:
                self._send(404, {"error": "unknown room"})
                return True
            sweep_expired_invites(room)
            caller = self._room_bearer(room)
            if caller is None:
                self._send(401, {"error": "room bearer token required"})
                return True
            if rest == []:
                self._send(200, self._room_public(room, caller))
                return True
            if rest == ["policy"]:
                self._send(200, self._room_policy(room))
                return True
            if rest == ["invites"]:
                # Owner-only invite lifecycle listing: metadata only, never
                # token hashes or raw tokens.
                if room["members"].get(caller, {}).get("role") != "owner":
                    self._send(403, {"error": "only the room owner can list invites"})
                    return True
                sweep_expired_invites(room)
                self._send(200, {"room_id": rid,
                                 "invites": [invite_public(inv)
                                             for inv in room["invites"].values()]})
                return True
            if rest == ["state"]:
                out = _public_room_state_locked(room)
                self._send(200, out)
                return True
            if rest == ["world"]:
                with room_scope(room):
                    snap = world.snapshot(state)
                snap["authenticated"] = True
                self._send(200, snap)
                return True
            # Rewrite into the lobby path so the shared implementation serves
            # it on the room's isolated partition.
            rewritten = "/api/" + "/".join(rest)
            if parsed.query:
                rewritten += "?" + parsed.query
            global _active_caller
            _active_caller = caller
            try:
                with room_scope(room):
                    self._dispatch_get(["api"] + rest, urlparse(rewritten))
            finally:
                _active_caller = None
        return True

    def _room_stream_valid(self, rid, token, agent_id, sub):
        """Revalidate a room SSE subscription: the room must exist, the agent
        must still be a member, and the bearer token must still map to them.
        Call with or without lock (takes it itself)."""
        with lock:
            if sub not in subscribers:
                return False
            room = state["rooms"].get(rid)
            if room is None:
                return False
            if agent_id not in room.get("members", {}):
                return False
            if room["auth"].get(token_hash(token)) != agent_id:
                return False
            return True

    def _room_stream_close(self, sub):
        """Close a room SSE stream and purge any queued private payloads.

        Also force close_connection: the handler sends
        "Connection: keep-alive" (which flips close_connection off in
        CPython's send_header), so without this the server would park the
        socket waiting for a next request instead of delivering EOF."""
        with lock:
            while True:
                try:
                    sub.get_nowait()
                except queue.Empty:
                    break
            subscribers.pop(sub, None)
            sse_owner.pop(sub, None)
        self.close_connection = True

    def _room_sse(self, rid, parsed):
        """Room-scoped server-sent events. The bearer token travels in the
        Authorization header (fetch streaming); native EventSource clients
        that cannot set headers may use ?token= instead (requires TLS when the
        server is ever exposed beyond loopback). Membership is revalidated
        before replay, on every delivery and on idle; revoked or deleted
        streams are closed with their queued payloads purged."""
        qs = parse_qs(parsed.query)
        try:
            since = int(qs.get("since", [0])[0])
        except (ValueError, TypeError):
            since = 0
        token = None
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer "):].strip() or None
        if not token:
            token = qs.get("token", [None])[0]
        sub = queue.Queue(maxsize=256)
        with lock:
            room = state["rooms"].get(rid)
            if room is None:
                self._send(404, {"error": "unknown room"})
                return True
            agent_id = room["auth"].get(token_hash(token)) if token else None
            if agent_id not in room["members"]:
                self._send(401, {"error": "room bearer token required"})
                return True
            subscribers[sub] = rid
            sse_owner[sub] = agent_id
            replay = [ev for ev in room["events"] if ev["seq"] > since]
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.connection.settimeout(20)
            for ev in replay:
                if not self._room_stream_valid(rid, token, agent_id, sub):
                    self._room_stream_close(sub)
                    return True
                self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
            self.wfile.flush()
            while True:
                if not self._room_stream_valid(rid, token, agent_id, sub):
                    self._room_stream_close(sub)
                    return True
                try:
                    payload = sub.get(timeout=15)
                except queue.Empty:
                    with lock:
                        if sub not in subscribers:
                            # Same keep-alive trap as _room_stream_close:
                            # force the socket closed so the client sees EOF.
                            self.close_connection = True
                            break
                    payload = b": ping\n\n"
                self.wfile.write(payload)
                self.wfile.flush()
        except (OSError, TimeoutError):
            pass
        finally:
            with lock:
                subscribers.pop(sub, None)
                sse_owner.pop(sub, None)
        return True

    def _room_route_post(self, parts, body):
        """Route POST /api/rooms/... . Called with lock held. True = handled."""
        if parts[:2] != ["api", "rooms"]:
            return False
        if len(parts) == 2:
            # Room creation is operator-gated in public mode; rooms are never
            # publicly creatable.
            if not self._operator_ok():
                self._send(403, {"error": "operator token required"})
                return True
            self._room_create(body)
            return True
        room = state["rooms"].get(parts[2])
        if room is None:
            self._send(404, {"error": "unknown room"})
            return True
        rest = parts[3:]
        sweep_expired_invites(room)
        if rest == ["join"]:
            self._room_join(room, body)
            return True
        caller = self._room_bearer(room)
        if caller is None:
            self._send(401, {"error": "room bearer token required"})
            return True
        if rest == ["a2a"]:
            # Room-scoped JSON-RPC with the bearer caller bound to every
            # nested operation (same authorization rules as REST).
            self._room_a2a(room, caller, body)
            return True
        if rest == ["invites"]:
            self._room_invite_create(room, caller, body)
            return True
        if len(rest) == 3 and rest[0] == "invites" and rest[2] == "revoke":
            self._room_invite_revoke(room, caller, rest[1])
            return True
        if len(rest) == 3 and rest[0] == "members" and rest[2] == "remove":
            self._room_member_remove(room, caller, rest[1])
            return True
        if rest == ["leave"]:
            self._room_leave(room, caller)
            return True
        if rest == ["delete"]:
            self._room_delete(room, caller)
            return True
        err = self._enforce_room_caller(room, caller, rest, body)
        if err:
            self._send(err["code"], {"error": err["error"]})
            return True
        if rest[:2] == ["agents", "register"]:
            # No public join: membership is invite-only.
            self._send(403, {"error": "room membership is invite-only",
                             "join": "/api/rooms/%s/join" % room["id"]})
            return True
        global _active_caller
        _active_caller = caller
        try:
            with room_scope(room):
                sweep_expired_claims()
                self._dispatch_post(["api"] + rest, body)
        finally:
            _active_caller = None
        return True

    def _enforce_room_caller(self, room, caller, rest, body):
        """In rooms the bearer token is the identity: URL/body agent ids must be
        the caller's own. Returns an error dict or None."""
        is_owner = room["members"].get(caller, {}).get("role") == "owner"
        if len(rest) >= 3 and rest[0] == "agents" \
                and rest[2] in ("heartbeat", "presence"):
            if rest[1] != caller:
                return {"code": 403,
                        "error": "bearer token does not match agent"}
        if rest == ["social"]:
            if body.get("agent_id") != caller:
                return {"code": 403,
                        "error": "agent_id must match the bearer token"}
        if rest == ["messages"]:
            if body.get("from_agent") != caller:
                return {"code": 403,
                        "error": "from_agent must match the bearer token"}
        if len(rest) == 3 and rest[0] == "tasks" and rest[2] in (
                "claim", "progress", "artifacts", "complete"):
            if body.get("agent_id") != caller:
                return {"code": 403,
                        "error": "agent_id must match the bearer token"}
        if len(rest) == 3 and rest[0] == "tasks" and rest[2] == "verify":
            if body.get("verifier_agent_id") != caller:
                return {"code": 403,
                        "error": "verifier_agent_id must match the bearer token"}
        if len(rest) == 3 and rest[0] == "tasks" and rest[2] in (
                "cancel", "clarify"):
            task = room["tasks"].get(rest[1])
            if task is None:
                return None  # the shared handler reports the 404
            holder = task.get("agent_id")
            if holder not in (None, caller) and not is_owner:
                return {"code": 403, "error":
                        "only the claiming agent or the room owner can cancel"}
            body["by"] = caller  # the ledger records the true actor
        if len(rest) == 3 and rest[0] == "goals" and rest[2] == "context":
            if body.get("agent_id") != caller:
                return {"code": 403,
                        "error": "agent_id must match the bearer token"}
        return None

    def _room_create(self, body):
        """Bootstrap: creating a room registers the creator as its owner agent
        and returns their bearer token. There is no prior credential to check;
        on any non-loopback deployment this endpoint must sit behind the
        deployer's own access control (see docs/ROOMS.md)."""
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            return self._send(400, {"error": "room name is required"})
        space = body.get("space", "classroom")
        if space not in ("classroom", "playground"):
            return self._send(400, {"error": "invalid space"})
        if "social_enabled" in body and not isinstance(body["social_enabled"], bool):
            return self._send(400, {"error": "social_enabled must be boolean"})
        if len(state["rooms"]) >= 64:
            return self._send(409, {"error": "room limit reached"})
        room = blank_room(name.strip())
        aid = new_id("agent")
        agent = build_agent_record(body, aid, 0, room["id"], space)
        room["agents"][aid] = agent
        room["owner_agent_id"] = aid
        room["members"][aid] = {"role": "owner", "joined_at": utcnow(),
                                "name": agent["name"]}
        token = new_bearer_token()
        room["auth"][token_hash(token)] = aid
        state["rooms"][room["id"]] = room
        with room_scope(room):
            ledger_append("room_created", {"name": room["name"]}, actor=aid)
            save_state()
        emit("room_created", {"room_id": room["id"], "name": room["name"]})
        return self._send(200, {"room": self._room_public(room, aid),
                                "agent": agent, "token": token})

    def _room_invite_create(self, room, caller, body):
        if room["members"].get(caller, {}).get("role") != "owner":
            return self._send(403, {"error": "only the room owner can invite"})
        if len(room["members"]) >= ROOM_MAX_AGENTS:
            return self._send(409, {"error": "room is full",
                                    "max_agents": ROOM_MAX_AGENTS})
        ttl = body.get("ttl_seconds", INVITE_DEFAULT_TTL)
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) \
                or not 60 <= ttl <= 30 * 86400:
            return self._send(400, {"error": "ttl_seconds must be 60..2592000"})
        iid = new_id("invite")
        token = new_invite_token()
        inv = {"id": iid, "token_hash": token_hash(token),
               "created_by": caller, "created_at": utcnow(),
               "expires_at": utcnow() + ttl, "ttl_seconds": ttl,
               "label": str(body.get("label", ""))[:80],
               "used": False, "used_by": None, "used_at": None,
               "revoked": False}
        room["invites"][iid] = inv
        with room_scope(room):
            ledger_append("invite_created",
                          {"invite_id": iid, "ttl_seconds": ttl,
                           "label": inv["label"]}, actor=caller)
            save_state()
        join_block = {"method": "POST",
                      "endpoint": "/api/rooms/%s/join" % room["id"],
                      "body": {"invite_token": token,
                               "name": "Agent name"}}
        if PUBLIC_URL:
            join_block["join_url"] = "%s/api/rooms/%s/join" % (PUBLIC_URL,
                                                               room["id"])
        return self._send(200, {"invite_id": iid, "token": token,
                                "room_id": room["id"],
                                "join": join_block,
                                "expires_at": inv["expires_at"]})

    def _join_client_ip(self):
        """Client IP for join rate limiting. Proxy headers are honored only
        when the direct TCP peer is an explicitly trusted proxy
        (PLAYGROUNDS_TRUSTED_PROXIES); otherwise the peer address is used so
        a spoofed X-Forwarded-For cannot mint fresh buckets."""
        peer = self.client_address[0]
        if peer.lower() in TRUSTED_PROXIES:
            fwd = self.headers.get("CF-Connecting-IP") or ""
            if not fwd:
                fwd = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            if fwd:
                return fwd
        return peer

    def _join_limited(self):
        """Anti-bruteforce budget for room joins. Only failed guesses consume
        it, so legitimate joins (up to the 64-member cap) are never throttled."""
        return not _join_ratelimit_ok(self._join_client_ip())

    def _room_join(self, room, body):
        token = body.get("invite_token")
        if not isinstance(token, str) or not token:
            if self._join_limited():
                return self._send(429, {"error": "too many join attempts; slow down"})
            return self._send(403, {"error": "a valid invite_token is required; "
                                             "rooms have no public join"})
        th = token_hash(token)
        inv = next((c for c in room["invites"].values()
                    if hmac.compare_digest(c["token_hash"], th)), None)
        if inv is None or inv["revoked"]:
            if self._join_limited():
                return self._send(429, {"error": "too many join attempts; slow down"})
            return self._send(403, {"error": "unknown or revoked invite"})
        if inv["used"]:
            return self._send(410, {"error": "invite already used (single-use)"})
        if inv["expires_at"] < utcnow():
            return self._send(410, {"error": "invite expired"})
        if len(room["members"]) >= ROOM_MAX_AGENTS:
            return self._send(409, {"error": "room is full",
                                    "max_agents": ROOM_MAX_AGENTS})
        space = body.get("space", "classroom")
        if space not in ("classroom", "playground"):
            return self._send(400, {"error": "invalid space"})
        if "social_enabled" in body and not isinstance(body["social_enabled"], bool):
            return self._send(400, {"error": "social_enabled must be boolean"})
        with room_scope(room):
            if space == "classroom" and not world.classroom_available(state, None, None):
                return self._send(409, {"error": "classroom is full",
                                        "max_agents": ROOM_MAX_AGENTS})
        aid = new_id("agent")
        agent = build_agent_record(body, aid, len(room["agents"]), room["id"],
                                   space)
        room["agents"][aid] = agent
        room["members"][aid] = {"role": "member", "joined_at": utcnow(),
                                "name": agent["name"]}
        bt = new_bearer_token()
        room["auth"][token_hash(bt)] = aid
        inv["used"] = True
        inv["used_by"] = aid
        inv["used_at"] = utcnow()
        with room_scope(room):
            ledger_append("member_joined", {"name": agent["name"],
                                           "invite_id": inv["id"]}, actor=aid)
            # Membership events are emitted INSIDE the scope so only room
            # subscribers receive member names/ids — never the lobby.
            emit("member_joined", {"room_id": room["id"], "agent_id": aid,
                                   "name": agent["name"]})
            save_state()
        return self._send(200, {"room": self._room_public(room, aid),
                                "agent": agent, "token": bt})

    def _room_invite_revoke(self, room, caller, invite_id):
        if room["members"].get(caller, {}).get("role") != "owner":
            return self._send(403, {"error": "only the room owner can revoke invites"})
        inv = room["invites"].get(invite_id)
        if inv is None:
            return self._send(404, {"error": "unknown invite"})
        if inv["used"]:
            return self._send(409, {"error": "invite already used"})
        inv["revoked"] = True
        with room_scope(room):
            ledger_append("invite_revoked", {"invite_id": invite_id},
                          actor=caller)
            save_state()
        return self._send(200, {"ok": True, "invite_id": invite_id})

    def _remove_member(self, room, caller, target_id):
        """Shared removal: release claims, invalidate tokens, drop the agent."""
        with room_scope(room):
            released = release_agent_claims(target_id)
            for th in [th for th, aid in room["auth"].items()
                       if aid == target_id]:
                del room["auth"][th]
            agent = room["agents"].pop(target_id, None)
            room["members"].pop(target_id, None)
            ledger_append("member_removed",
                          {"agent_id": target_id,
                           "name": (agent or {}).get("name"),
                           "claims_released": released}, actor=caller)
            # Inside the scope: room subscribers are notified, the lobby is not.
            emit("member_removed", {"room_id": room["id"],
                                    "agent_id": target_id})
            save_state()
        # Close the removed member's live streams and purge queued payloads.
        with lock:
            _close_room_streams(room["id"], target_id)
        return released

    def _room_member_remove(self, room, caller, target_id):
        if room["members"].get(caller, {}).get("role") != "owner":
            return self._send(403, {"error": "only the room owner can remove members"})
        if target_id == room["owner_agent_id"]:
            return self._send(400, {"error": "the owner cannot be removed; "
                                             "delete the room instead"})
        if target_id not in room["members"]:
            return self._send(404, {"error": "unknown member"})
        released = self._remove_member(room, caller, target_id)
        return self._send(200, {"ok": True, "agent_id": target_id,
                                "claims_released": released})

    def _room_leave(self, room, caller):
        if caller == room["owner_agent_id"]:
            return self._send(400, {"error": "the owner cannot leave; "
                                             "delete the room instead"})
        if caller not in room["members"]:
            return self._send(404, {"error": "not a member"})
        released = self._remove_member(room, caller, caller)
        return self._send(200, {"ok": True, "claims_released": released})

    def _room_delete(self, room, caller):
        if room["members"].get(caller, {}).get("role") != "owner":
            return self._send(403, {"error": "only the room owner can delete the room"})
        rid = room["id"]
        with lock:
            _close_room_streams(rid)
            del state["rooms"][rid]
            save_state()
        return self._send(200, {"ok": True, "room_id": rid})


    def _room_a2a(self, room, caller, body):
        """Room-scoped A2A JSON-RPC. Every nested operation is bound to the
        bearer-authenticated caller, with the same authorization rules as the
        REST protocol: task/send records the caller as actor, task/cancel
        enforces the claiming-agent-or-owner rule (no by="a2a" bypass)."""
        mid = body.get("id")
        method = body.get("method", "")
        params = body.get("params", {}) or {}

        def ok(result):
            return self._send(200, {"jsonrpc": "2.0", "id": mid,
                                    "result": result})

        def err(code, message):
            return self._send(200, {"jsonrpc": "2.0", "id": mid,
                                    "error": {"code": code, "message": message}})

        is_owner = room["members"].get(caller, {}).get("role") == "owner"
        if method == "card/get":
            with room_scope(room):
                card = playground_card()
            card["room_id"] = room["id"]
            return ok(card)
        if method == "task/send":
            gid = params.get("goal_id")
            if not gid:
                return err(-32602, "goal_id required")
            with room_scope(room):
                task, e = create_task(gid, params, actor=caller)
            if e:
                return err(-32000, e["error"])
            return ok({"task_id": task["id"], "status": task["status"],
                       "topology": task.get("topology")})
        if method == "task/get":
            tid = params.get("task_id")
            with room_scope(room):
                task = state["tasks"].get(tid)
                if not task:
                    return err(-32000, "unknown task")
                arts = [state["artifacts"][a]
                        for a in task.get("artifact_ids", [])
                        if a in state["artifacts"]]
                task = dict(task)
            return ok({"task": task, "artifacts": arts})
        if method == "task/cancel":
            tid = params.get("task_id")
            with room_scope(room):
                task = state["tasks"].get(tid)
                if not task:
                    return err(-32000, "unknown task")
                holder = task.get("agent_id")
                if holder not in (None, caller) and not is_owner:
                    return err(-32001, "only the claiming agent or the room "
                                       "owner can cancel")
                t = cancel_task(tid, by=caller,
                                reason=params.get("reason", "a2a cancel"))
            if not t:
                return err(-32000, "unknown or terminal task")
            return ok({"task_id": t["id"], "status": t["status"]})
        return err(-32601, f"method not found: {method}")


    def _handle_a2a(self, body):
        mid = body.get("id")
        method = body.get("method", "")
        params = body.get("params", {}) or {}

        def ok(result):
            return self._send(200, {"jsonrpc": "2.0", "id": mid,
                                    "result": result})

        def err(code, message):
            return self._send(200, {"jsonrpc": "2.0", "id": mid,
                                    "error": {"code": code, "message": message}})

        if method == "card/get":
            with lock:
                return ok(playground_card())
        if method == "task/send":
            gid = params.get("goal_id")
            if not gid:
                return err(-32602, "goal_id required")
            task, e = create_task(gid, params, actor="a2a")
            if e:
                return err(-32000, e["error"])
            return ok({"task_id": task["id"], "status": task["status"],
                       "topology": task.get("topology")})
        if method == "task/get":
            tid = params.get("task_id")
            with lock:
                task = state["tasks"].get(tid)
                if not task:
                    return err(-32000, "unknown task")
                arts = [state["artifacts"][a] for a in task.get("artifact_ids", [])
                        if a in state["artifacts"]]
            return ok({"task": task, "artifacts": arts})
        if method == "task/cancel":
            t = cancel_task(params.get("task_id"), by="a2a",
                            reason=params.get("reason", "a2a cancel"))
            if not t:
                return err(-32000, "unknown or terminal task")
            return ok({"task_id": t["id"], "status": t["status"]})
        return err(-32601, f"method not found: {method}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Playgrounds protocol server v0.2 on http://127.0.0.1:{PORT}", flush=True)
    server.serve_forever()
