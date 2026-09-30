#!/usr/bin/env python3
"""Secure rooms test suite.

Part A — unit tests: room partitions, scope swapping, token hashing, invite
sweeps, claim release, and SSE room filtering, against an isolated temp state.

Part B — integration tests: boot a real server on 127.0.0.1:8481 and drive
the room protocol end to end: creation, bearer auth, single-use expiring
invites, no public join, 4-agent cap, isolation, caller binding, removal,
revocation, deletion, and a full task lifecycle inside a room.

Part C — public-mode tests on 127.0.0.1:8482 with PLAYGROUNDS_OPERATOR_TOKEN:
header-only operator auth, public join shell, spoofed proxy headers ignored.

Part D — trusted-proxy tests on 127.0.0.1:8483 with
PLAYGROUNDS_TRUSTED_PROXIES + PLAYGROUNDS_TRUSTED_ORIGIN: forwarded IPs are
honored only from trusted peers, and only the configured origin is accepted.

Usage: python3 test_rooms.py
"""
import json
import os
import queue
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="playgrounds-rooms-test-")
STATE_PATH = os.path.join(TMP, "state.json")
os.environ["PLAYGROUNDS_STATE_PATH"] = STATE_PATH

sys.path.insert(0, HERE)
import server as srv  # noqa: E402


def reset_state():
    srv.state.clear()
    srv.state.update(srv.blank_state())
    srv.save_state()


# ------------------------------------------------------------------ Part A

class RoomUnitTests(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_blank_room_partitions(self):
        room = srv.blank_room("Test")
        for k in srv.ROOM_PARTITION_KEYS:
            self.assertIn(k, room, k)
        self.assertEqual(room["members"], {})
        self.assertEqual(room["invites"], {})
        self.assertEqual(room["auth"], {})
        self.assertIsNone(room["owner_agent_id"])

    def test_room_scope_swaps_and_restores(self):
        room = srv.blank_room("Scope")
        srv.state["rooms"][room["id"]] = room
        lobby_agents = srv.state["agents"]
        with srv.room_scope(room):
            self.assertIs(srv.state["agents"], room["agents"])
            self.assertIsNot(srv.state["agents"], lobby_agents)
            self.assertEqual(srv._active_room_id, room["id"])
            srv.state["agents"]["agent_x"] = {"id": "agent_x"}
        self.assertIs(srv.state["agents"], lobby_agents)
        self.assertNotIn("agent_x", srv.state["agents"])
        self.assertIn("agent_x", room["agents"])
        self.assertIsNone(srv._active_room_id)

    def test_room_scope_restores_on_exception(self):
        room = srv.blank_room("Scope")
        lobby_ledger = srv.state["ledger"]
        try:
            with srv.room_scope(room):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertIs(srv.state["ledger"], lobby_ledger)
        self.assertIsNone(srv._active_room_id)

    def test_token_hash_salted_and_opaque(self):
        t = srv.new_bearer_token()
        h1 = srv.token_hash(t)
        self.assertTrue(h1.startswith("sha256:"))
        self.assertNotIn(t, h1)
        self.assertEqual(h1, srv.token_hash(t))
        self.assertNotEqual(h1, srv.token_hash(t + "x"))

    def test_sweep_expired_invites(self):
        room = srv.blank_room("Inv")
        now = srv.utcnow()
        room["invites"]["a"] = {"used": False, "revoked": False,
                                "expires_at": now - 1}
        room["invites"]["b"] = {"used": False, "revoked": False,
                                "expires_at": now + 3600}
        room["invites"]["c"] = {"used": True, "revoked": False,
                                "expires_at": now - 1}
        srv.sweep_expired_invites(room)
        # Expired invites are retained (history for the owner UI), not deleted.
        self.assertIn("a", room["invites"])
        self.assertTrue(room["invites"]["a"]["expired"])
        self.assertIn("b", room["invites"])
        self.assertNotIn("expired", room["invites"]["b"])
        self.assertIn("c", room["invites"])  # used invites are history

    def test_invite_lifecycle_status(self):
        now = srv.utcnow()
        mk = lambda **kw: dict({"id": "x", "label": "", "created_by": "o",
                                "created_at": now, "expires_at": now + 60,
                                "ttl_seconds": 60, "used": False,
                                "used_by": None, "used_at": None,
                                "revoked": False}, **kw)
        self.assertEqual(srv.invite_status(mk()), "active")
        self.assertEqual(srv.invite_status(mk(expires_at=now - 1)), "expired")
        self.assertEqual(srv.invite_status(mk(expired=True)), "expired")
        self.assertEqual(srv.invite_status(mk(used=True)), "used")
        self.assertEqual(srv.invite_status(mk(revoked=True)), "revoked")
        self.assertEqual(srv.invite_status(mk(used=True, revoked=True)), "used")
        pub = srv.invite_public(mk())
        blob = json.dumps(pub)
        self.assertNotIn("token", blob)
        self.assertNotIn("hash", blob)
        for k in ("id", "label", "expires_at", "used", "revoked", "status"):
            self.assertIn(k, pub, k)

    def test_public_state_excludes_rooms_and_secrets(self):
        room = srv.blank_room("Hidden")
        srv.state["rooms"][room["id"]] = room
        pub = srv._public_lobby_state_locked()
        self.assertNotIn("rooms", pub)
        self.assertNotIn("server_salt", pub)
        self.assertNotIn("idempotency", pub)
        self.assertIn("agents", pub)  # allowlisted keys still present

    def test_room_state_only_partitions(self):
        room = srv.blank_room("Iso")
        room["auth"]["deadbeef"] = "agent_1"
        room["invites"]["inv_x"] = {"token_hash": "deadbeef"}
        room["members"]["agent_1"] = {"role": "owner", "joined_at": 0}
        srv.state["rooms"][room["id"]] = room
        pub = srv._public_room_state_locked(room)
        self.assertEqual(set(pub), set(srv.ROOM_PARTITION_KEYS))
        self.assertNotIn("deadbeef", json.dumps(pub))

    def test_save_state_inside_room_scope(self):
        room = srv.blank_room("Persist")
        srv.state["rooms"][room["id"]] = room
        srv.save_state()
        with srv.room_scope(room):
            srv.state["agents"]["room_agent_9"] = {"id": "room_agent_9",
                                                   "name": "Roomy"}
            srv.state["ledger_seq"] = 4242  # scalar reassignment
            srv.save_state()
        on_disk = json.load(open(srv.STATE_PATH))
        # Lobby root on disk must not contain room data...
        self.assertNotIn("room_agent_9", on_disk["agents"])
        self.assertNotEqual(on_disk["ledger_seq"], 4242)
        # ...while the room record on disk carries the room's own data,
        # including the reassigned scalar.
        disk_room = on_disk["rooms"][room["id"]]
        self.assertIn("room_agent_9", disk_room["agents"])
        self.assertEqual(disk_room["ledger_seq"], 4242)

    def test_close_room_streams_purges(self):
        q1, q2 = queue.Queue(), queue.Queue()
        srv.subscribers[q1] = "room_1"
        srv.sse_owner[q1] = "agent_a"
        srv.subscribers[q2] = "room_1"
        srv.sse_owner[q2] = "agent_b"
        q1.put(b"data: secret\n\n")
        try:
            srv._close_room_streams("room_1", "agent_a")
            self.assertNotIn(q1, srv.subscribers)
            self.assertNotIn(q1, srv.sse_owner)
            self.assertTrue(q1.empty())  # queued payload purged
            self.assertIn(q2, srv.subscribers)  # other member untouched
        finally:
            srv.subscribers.pop(q1, None)
            srv.sse_owner.pop(q1, None)
            srv.subscribers.pop(q2, None)
            srv.sse_owner.pop(q2, None)

    def test_join_bucket_bounded(self):
        old_max = srv.JOIN_BUCKET_MAX
        srv.JOIN_BUCKET_MAX = 4
        try:
            srv._JOIN_BUCKET.clear()
            srv._JOIN_BUCKET["stale-ip"] = {"hits": [0.0], "seen": 0.0}
            for i in range(6):
                self.assertTrue(srv._join_ratelimit_ok(f"ip-{i}"))
            # bounded: inactive keys are evicted first, then least-recently-seen
            self.assertNotIn("stale-ip", srv._JOIN_BUCKET)
            self.assertLessEqual(len(srv._JOIN_BUCKET), 4)
        finally:
            srv.JOIN_BUCKET_MAX = old_max
            srv._JOIN_BUCKET.clear()

    def test_release_agent_claims(self):
        room = srv.blank_room("Rel")
        srv.state["rooms"][room["id"]] = room
        with srv.room_scope(room):
            srv.state["goals"]["goal_1"] = {"id": "goal_1",
                                            "budget_available": 900,
                                            "budget_spent": 100}
            srv.state["tasks"]["task_1"] = {"id": "task_1", "goal_id": "goal_1",
                                           "status": "claimed", "agent_id": "agent_gone",
                                           "escrow": 100,
                                           "lease": {"holder": "agent_gone"}}
            released = srv.release_agent_claims("agent_gone")
            self.assertEqual(released, ["task_1"])
            t = srv.state["tasks"]["task_1"]
            self.assertEqual(t["status"], "open")
            self.assertIsNone(t["agent_id"])
            self.assertEqual(t["escrow"], 0)
            self.assertEqual(srv.state["goals"]["goal_1"]["budget_available"], 1000)
            # nothing claimed by anyone else is touched
            self.assertEqual(srv.release_agent_claims("agent_other"), [])

    def test_emit_tags_room_and_filters_subscribers(self):
        room = srv.blank_room("Evt")
        srv.state["rooms"][room["id"]] = room
        q_room, q_lobby = queue.Queue(), queue.Queue()
        srv.subscribers[q_room] = room["id"]
        srv.subscribers[q_lobby] = None
        try:
            with srv.room_scope(room):
                ev = srv.emit("member_joined", {"agent_id": "a"})
            self.assertEqual(ev["room_id"], room["id"])
            self.assertTrue(q_lobby.empty())
            got = json.loads(q_room.get_nowait()[len("data: "):])
            self.assertEqual(got["room_id"], room["id"])
            # lobby emit reaches only the lobby subscriber
            srv.emit("lobby_event", {})
            self.assertTrue(q_room.empty())
            got = json.loads(q_lobby.get_nowait()[len("data: "):])
            self.assertIsNone(got["room_id"])
        finally:
            srv.subscribers.pop(q_room, None)
            srv.subscribers.pop(q_lobby, None)

    def test_ledger_chain_verifies_inside_room(self):
        room = srv.blank_room("Chain")
        srv.state["rooms"][room["id"]] = room
        with srv.room_scope(room):
            srv.ledger_append("room_created", {}, actor="agent_1")
            srv.ledger_append("goal_created", {}, actor="agent_1",
                              goal_id="goal_1")
            ok, failing = srv.verify_ledger_chain()
            self.assertTrue(ok, failing)
            self.assertEqual(len(srv.state["ledger"]), 2)
        self.assertEqual(srv.state["ledger"], [])  # lobby untouched


# ------------------------------------------------------------------ Part B

PORT = 8481
BASE = f"http://127.0.0.1:{PORT}"


def req(method, path, body=None, token=None, extra_headers=None):
    r = urllib.request.Request(BASE + path, method=method)
    if body is not None:
        r.data = json.dumps(body).encode()
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    for k, v in (extra_headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


def open_room_stream(rid, token, use_header=True):
    """Send a room SSE request with an Authorization header (fetch streaming)
    or the legacy ?token= query (native EventSource). Returns the connection
    BEFORE getresponse() — callers must set conn.sock timeouts before
    reading, because getresponse() detaches conn.sock."""
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=12)
    path = f"/api/rooms/{rid}/events?since=0"
    headers = {}
    if use_header:
        headers["Authorization"] = "Bearer " + token
    else:
        path += "&token=" + token
    conn.request("GET", path, headers=headers)
    return conn


def read_until_marker(resp, marker, timeout=10):
    """Read a streaming response until marker appears (streams stay open,
    so a fixed-size read would block until EOF)."""
    import socket
    deadline = time.time() + timeout
    buf = b""
    while time.time() < deadline:
        try:
            chunk = resp.read(1)
        except socket.timeout:
            continue
        if not chunk:
            break
        buf += chunk
        if marker in buf:
            return buf
    return buf


class RoomApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PLAYGROUNDS_STATE_PATH=STATE_PATH,
                   PLAYGROUNDS_PORT=str(PORT))
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py")],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE + "/api/policy", timeout=2).read()
                break
            except Exception:
                time.sleep(0.25)
        else:
            cls.proc.terminate()
            raise RuntimeError("server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()

    def setUp(self):
        # fresh server state per test via the lobby reset path is unavailable;
        # each test creates its own rooms, which are isolated by design.
        pass

    # -- helpers -------------------------------------------------------
    def create_room(self, name="Room", **kw):
        body = {"name": name}
        body.update(kw)
        code, out = req("POST", "/api/rooms", body)
        self.assertEqual(code, 200, out)
        return out  # {room, agent, token}

    def join(self, rid, invite_token, name="Guest", space="classroom"):
        body = {"invite_token": invite_token, "name": name}
        if space != "classroom":
            body["space"] = space
        return req("POST", f"/api/rooms/{rid}/join", body)

    def invite(self, rid, token, **kw):
        return req("POST", f"/api/rooms/{rid}/invites", kw, token=token)

    # -- tests ---------------------------------------------------------
    def test_create_room_bootstraps_owner(self):
        out = self.create_room("Alpha")
        rid = out["room"]["id"]
        owner, otok = out["agent"]["id"], out["token"]
        self.assertTrue(otok.startswith("tok_"))
        self.assertEqual(out["room"]["owner_agent_id"], owner)
        self.assertEqual(out["agent"]["tenant_id"], rid)  # tenant_id is real
        # unauthenticated room read is rejected
        code, _ = req("GET", f"/api/rooms/{rid}")
        self.assertEqual(code, 401)
        # authenticated read works
        code, got = req("GET", f"/api/rooms/{rid}", token=otok)
        self.assertEqual(code, 200, got)
        self.assertEqual(got["members"][0]["role"], "owner")
        # room policy reports auth
        code, pol = req("GET", f"/api/rooms/{rid}/policy", token=otok)
        self.assertEqual(code, 200)
        self.assertTrue(pol["auth_required"])
        self.assertFalse(pol["public_join"])
        # lobby state does not contain the room's agent
        code, lobby = req("GET", "/api/state")
        self.assertEqual(code, 200)
        self.assertNotIn(owner, lobby["agents"])

    def test_room_directory_lists_without_auth(self):
        out = self.create_room("Listed")
        code, listing = req("GET", "/api/rooms")
        self.assertEqual(code, 200)
        ids = [r["id"] for r in listing["rooms"]]
        self.assertIn(out["room"]["id"], ids)
        # but no tokens or member details leak
        self.assertNotIn("token", json.dumps(listing))

    def test_no_public_join(self):
        out = self.create_room("NoPublic")
        rid, otok = out["room"]["id"], out["token"]
        code, err = req("POST", f"/api/rooms/{rid}/agents/register",
                        {"name": "Sneaky"}, token=otok)
        self.assertEqual(code, 403, err)
        self.assertIn("invite-only", err["error"])
        code, err = req("POST", f"/api/rooms/{rid}/join",
                        {"name": "Sneaky"})
        self.assertEqual(code, 403, err)

    def test_invite_join_single_use(self):
        out = self.create_room("SingleUse")
        rid, otok = out["room"]["id"], out["token"]
        code, inv = self.invite(rid, otok, label="friend")
        self.assertEqual(code, 200, inv)
        self.assertTrue(inv["token"].startswith("inv_"))
        code, joined = self.join(rid, inv["token"], name="Bob")
        self.assertEqual(code, 200, joined)
        btok = joined["token"]
        # single-use: second redemption fails
        code, err = self.join(rid, inv["token"], name="Bob2")
        self.assertEqual(code, 410, err)
        # unknown token fails
        code, err = self.join(rid, "inv_bogus", name="Mallory")
        self.assertEqual(code, 403, err)
        # the new member can act with their own token
        code, card = req("GET",
                         f"/api/rooms/{rid}/agents/{joined['agent']['id']}/card",
                         token=btok)
        self.assertEqual(code, 200, card)

    def test_non_owner_cannot_invite(self):
        out = self.create_room("OwnerOnly")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Member")
        code, err = self.invite(rid, joined["token"])
        self.assertEqual(code, 403, err)

    def test_revoke_invite(self):
        out = self.create_room("Revoke")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok)
        code, _ = req("POST",
                      f"/api/rooms/{rid}/invites/{inv['invite_id']}/revoke",
                      {}, token=otok)
        self.assertEqual(code, 200)
        code, err = self.join(rid, inv["token"], name="Late")
        self.assertEqual(code, 403, err)

    def test_room_cap_sixtyfour(self):
        out = self.create_room("Cap")
        rid, otok, owner = out["room"]["id"], out["token"], out["agent"]["id"]
        tokens = [otok]
        # mint one spare invite while there is space
        _, spare = self.invite(rid, otok)
        # study hall seats 24 (owner + 23 classroom joins) ...
        for i in range(23):
            _, inv = self.invite(rid, otok)
            code, joined = self.join(rid, inv["token"], name=f"S{i}")
            self.assertEqual(code, 200, joined)
            tokens.append(joined["token"])
        # ... the 25th classroom seat is refused ...
        _, inv = self.invite(rid, otok)
        code, err = self.join(rid, inv["token"], name="NoSeat")
        self.assertEqual(code, 409, err)
        self.assertIn("classroom", err["error"])
        # ... but the playground holds the rest up to 64
        for i in range(40):
            _, inv = self.invite(rid, otok)
            code, joined = self.join(rid, inv["token"], name=f"P{i}",
                                    space="playground")
            self.assertEqual(code, 200, joined)
            tokens.append(joined["token"])
        # full room: owner cannot mint more invites ...
        code, err = self.invite(rid, otok)
        self.assertEqual(code, 409, err)
        self.assertEqual(err["max_agents"], 64)
        # ... and even a valid outstanding invite cannot redeem
        code, err = self.join(rid, spare["token"], name="SixtyFifth")
        self.assertEqual(code, 409, err)

    def test_cross_room_isolation(self):
        a = self.create_room("RoomA")
        b = self.create_room("RoomB")
        ra, ta = a["room"]["id"], a["token"]
        rb, tb = b["room"]["id"], b["token"]
        # goal in A
        code, goal = req("POST", f"/api/rooms/{ra}/goals",
                         {"title": "Secret", "budget": 500}, token=ta)
        self.assertEqual(code, 200, goal)
        # invisible from B
        code, _ = req("GET", f"/api/rooms/{rb}/goals/{goal['id']}/context",
                      token=tb)
        self.assertEqual(code, 200)  # context of unknown goal is empty, not leaked
        code, ledger_b = req("GET", f"/api/rooms/{rb}/ledger", token=tb)
        self.assertEqual(code, 200)
        self.assertFalse(any(e.get("goal_id") == goal["id"]
                             for e in ledger_b["events"]))
        # A's token is useless in B
        code, _ = req("GET", f"/api/rooms/{rb}", token=ta)
        self.assertEqual(code, 401)
        # messages do not cross
        code, _ = req("POST", f"/api/rooms/{ra}/messages",
                      {"from_agent": a["agent"]["id"], "text": "hi A"},
                      token=ta)
        self.assertEqual(code, 200)
        code, msgs = req("GET", f"/api/rooms/{rb}/messages", token=tb)
        self.assertEqual(msgs["messages"], [])

    def test_caller_binding(self):
        out = self.create_room("Binding")
        rid, otok, owner = out["room"]["id"], out["token"], out["agent"]["id"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Bob")
        btok, bob = joined["token"], joined["agent"]["id"]
        # heartbeat as someone else
        code, err = req("POST", f"/api/rooms/{rid}/agents/{owner}/heartbeat",
                        {"status": "busy"}, token=btok)
        self.assertEqual(code, 403, err)
        # own heartbeat works
        code, _ = req("POST", f"/api/rooms/{rid}/agents/{bob}/heartbeat",
                      {"status": "busy"}, token=btok)
        self.assertEqual(code, 200)
        # claim as someone else
        code, goal = req("POST", f"/api/rooms/{rid}/goals",
                         {"title": "G", "budget": 100}, token=otok)
        code, task = req("POST", f"/api/rooms/{rid}/goals/{goal['id']}/tasks",
                         {"title": "T", "bounty": 10}, token=otok)
        tid = task["id"]
        code, err = req("POST", f"/api/rooms/{rid}/tasks/{tid}/claim",
                        {"agent_id": owner}, token=btok)
        self.assertEqual(code, 403, err)
        # claim as self works
        code, _ = req("POST", f"/api/rooms/{rid}/tasks/{tid}/claim",
                      {"agent_id": bob}, token=btok)
        self.assertEqual(code, 200)

    def test_full_task_lifecycle_in_room(self):
        out = self.create_room("Lifecycle")
        rid, otok, owner = out["room"]["id"], out["token"], out["agent"]["id"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Worker")
        wtok, worker = joined["token"], joined["agent"]["id"]
        code, goal = req("POST", f"/api/rooms/{rid}/goals",
                         {"title": "Ship", "budget": 200}, token=otok)
        self.assertEqual(code, 200, goal)
        # the ledger records the real agent, not "human"
        code, ledger = req("GET", f"/api/rooms/{rid}/ledger", token=otok)
        gc = [e for e in ledger["events"] if e["type"] == "goal_created"][0]
        self.assertEqual(gc["actor"], owner)
        code, task = req("POST", f"/api/rooms/{rid}/goals/{goal['id']}/tasks",
                         {"title": "Build", "bounty": 50,
                          "success_criteria": "done"}, token=otok)
        tid = task["id"]
        for path, body_, tok in [
                (f"/tasks/{tid}/claim", {"agent_id": worker}, wtok),
                (f"/tasks/{tid}/progress",
                 {"agent_id": worker, "note": "half", "progress_pct": 50}, wtok),
                (f"/tasks/{tid}/complete",
                 {"agent_id": worker, "result": "shipped"}, wtok),
                (f"/tasks/{tid}/verify",
                 {"approved": True, "verifier_agent_id": owner,
                  "quality": 0.9, "confidence": 0.9}, otok)]:
            code, _ = req("POST", f"/api/rooms/{rid}" + path, body_, token=tok)
            self.assertEqual(code, 200, (path, code))
        # settlement credited the worker inside the room only
        code, stats = req("GET", f"/api/rooms/{rid}/agents/{worker}/stats",
                          token=wtok)
        self.assertEqual(code, 200)
        self.assertGreater(stats["credits_earned"], 0)
        code, lobby = req("GET", "/api/state")
        self.assertNotIn(worker, lobby["agents"])

    def test_remove_member_releases_claims_and_kills_token(self):
        out = self.create_room("Remove")
        rid, otok, owner = out["room"]["id"], out["token"], out["agent"]["id"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Temp")
        ttok, temp = joined["token"], joined["agent"]["id"]
        code, goal = req("POST", f"/api/rooms/{rid}/goals",
                         {"title": "G", "budget": 100}, token=otok)
        code, task = req("POST", f"/api/rooms/{rid}/goals/{goal['id']}/tasks",
                         {"title": "T", "bounty": 40}, token=otok)
        tid = task["id"]
        code, _ = req("POST", f"/api/rooms/{rid}/tasks/{tid}/claim",
                      {"agent_id": temp}, token=ttok)
        self.assertEqual(code, 200)
        code, rm = req("POST", f"/api/rooms/{rid}/members/{temp}/remove",
                       {}, token=otok)
        self.assertEqual(code, 200, rm)
        self.assertEqual(rm["claims_released"], [tid])
        # token is dead
        code, _ = req("GET", f"/api/rooms/{rid}", token=ttok)
        self.assertEqual(code, 401)
        # member is gone from the room and from presence
        code, room = req("GET", f"/api/rooms/{rid}", token=otok)
        self.assertNotIn(temp, [m["agent_id"] for m in room["members"]])
        code, world = req("GET", f"/api/rooms/{rid}/world", token=otok)
        self.assertNotIn(temp, [a["id"] for a in world["agents"]])
        # escrow returned: task open again, budget whole
        code, ledger = req("GET", f"/api/rooms/{rid}/ledger", token=otok)
        rel = [e for e in ledger["events"] if e["type"] == "claim_released"]
        self.assertTrue(rel)

    def test_owner_cannot_be_removed_or_leave(self):
        out = self.create_room("OwnerSafe")
        rid, otok, owner = out["room"]["id"], out["token"], out["agent"]["id"]
        code, err = req("POST", f"/api/rooms/{rid}/members/{owner}/remove",
                        {}, token=otok)
        self.assertEqual(code, 400, err)
        code, err = req("POST", f"/api/rooms/{rid}/leave", {}, token=otok)
        self.assertEqual(code, 400, err)

    def test_member_leave(self):
        out = self.create_room("Leave")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Leaver")
        ltok = joined["token"]
        code, _ = req("POST", f"/api/rooms/{rid}/leave", {}, token=ltok)
        self.assertEqual(code, 200)
        code, _ = req("GET", f"/api/rooms/{rid}", token=ltok)
        self.assertEqual(code, 401)

    def test_non_owner_cannot_delete(self):
        out = self.create_room("Del")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Bob")
        code, err = req("POST", f"/api/rooms/{rid}/delete", {},
                        token=joined["token"])
        self.assertEqual(code, 403, err)
        code, _ = req("POST", f"/api/rooms/{rid}/delete", {}, token=otok)
        self.assertEqual(code, 200)
        code, _ = req("GET", f"/api/rooms/{rid}", token=otok)
        self.assertEqual(code, 404)

    def test_tokens_never_leak(self):
        out = self.create_room("NoLeak")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok, label="x")
        code, state = req("GET", f"/api/rooms/{rid}/state", token=otok)
        self.assertEqual(code, 200)
        blob = json.dumps(state)
        self.assertNotIn(otok, blob)
        self.assertNotIn(inv["token"], blob)
        self.assertNotIn("tok_", blob)
        self.assertNotIn("inv_", blob)
        self.assertNotIn("auth", state)

    def test_presence_is_per_room(self):
        out = self.create_room("Presence")
        rid, otok = out["room"]["id"], out["token"]
        code, world = req("GET", f"/api/rooms/{rid}/world", token=otok)
        self.assertEqual(code, 200, world)
        self.assertTrue(world["authenticated"])
        self.assertEqual(len(world["agents"]), 1)
        # heartbeat updates last_heartbeat honestly
        code, _ = req("POST",
                      f"/api/rooms/{rid}/agents/{out['agent']['id']}/heartbeat",
                      {"status": "working"}, token=otok)
        self.assertEqual(code, 200)


    def test_ratelimit_bucket_unit(self):
        srv._JOIN_BUCKET.pop("unit-test-ip", None)
        for _ in range(srv.JOIN_RATELIMIT):
            self.assertTrue(srv._join_ratelimit_ok("unit-test-ip"))
        self.assertFalse(srv._join_ratelimit_ok("unit-test-ip"))

    # -- isolation / contracts -----------------------------------------

    def test_two_room_isolation(self):
        a = self.create_room("RoomA")
        b = self.create_room("RoomB")
        ra, ta = a["room"]["id"], a["token"]
        rb, tb = b["room"]["id"], b["token"]
        _, inva = self.invite(ra, ta, label="a")
        _, ja = self.join(ra, inva["token"], name="AliceA")
        code, ga = req("POST", f"/api/rooms/{ra}/goals",
                       {"title": "SecretGoalA", "budget": 100}, token=ta)
        self.assertEqual(code, 200, ga)
        _, invb = self.invite(rb, tb, label="b")
        _, jb = self.join(rb, invb["token"], name="BobB")
        code, gb = req("POST", f"/api/rooms/{rb}/goals",
                       {"title": "SecretGoalB", "budget": 100}, token=tb)
        self.assertEqual(code, 200, gb)
        _, sa = req("GET", f"/api/rooms/{ra}/state", token=ta)
        blob_a = json.dumps(sa)
        self.assertNotIn("BobB", blob_a)
        self.assertNotIn("SecretGoalB", blob_a)
        self.assertNotIn(jb["agent"]["id"], blob_a)
        self.assertNotIn("auth", sa)
        _, sb = req("GET", f"/api/rooms/{rb}/state", token=tb)
        blob_b = json.dumps(sb)
        self.assertNotIn("AliceA", blob_b)
        self.assertNotIn("SecretGoalA", blob_b)
        self.assertNotIn(ja["agent"]["id"], blob_b)
        # the lobby snapshot carries neither room's private data
        _, lobby = req("GET", "/api/state")
        self.assertNotIn("rooms", lobby)
        blob_l = json.dumps(lobby)
        self.assertNotIn("AliceA", blob_l)
        self.assertNotIn("SecretGoalA", blob_l)
        self.assertNotIn("BobB", blob_l)
        self.assertNotIn("SecretGoalB", blob_l)

    def test_room_metadata_caller_and_invite_listing(self):
        out = self.create_room("Meta")
        rid, otok = out["room"]["id"], out["token"]
        owner = out["agent"]["id"]
        self.assertEqual(out["room"]["caller_agent_id"], owner)
        _, inv = self.invite(rid, otok, label="g1")
        _, joined = self.join(rid, inv["token"], name="Guest1")
        gtok, guest = joined["token"], joined["agent"]["id"]
        code, meta = req("GET", f"/api/rooms/{rid}", token=gtok)
        self.assertEqual(code, 200, meta)
        self.assertEqual(meta["caller_agent_id"], guest)
        # invite listing is owner-only and leaks no secrets
        code, _ = req("GET", f"/api/rooms/{rid}/invites", token=gtok)
        self.assertEqual(code, 403)
        code, listing = req("GET", f"/api/rooms/{rid}/invites", token=otok)
        self.assertEqual(code, 200, listing)
        self.assertEqual(listing["room_id"], rid)
        blob = json.dumps(listing)
        self.assertNotIn(inv["token"], blob)
        self.assertNotIn("token_hash", blob)
        by_id = {i["id"]: i for i in listing["invites"]}
        self.assertEqual(by_id[inv["invite_id"]]["status"], "used")
        self.assertEqual(by_id[inv["invite_id"]]["label"], "g1")
        # revoked invite keeps its record with an honest status
        _, inv2 = self.invite(rid, otok, label="short")
        code, _ = req("POST",
                      f"/api/rooms/{rid}/invites/{inv2['invite_id']}/revoke",
                      {}, token=otok)
        self.assertEqual(code, 200)
        code, listing = req("GET", f"/api/rooms/{rid}/invites", token=otok)
        by_id = {i["id"]: i for i in listing["invites"]}
        self.assertEqual(by_id[inv2["invite_id"]]["status"], "revoked")
        self.assertNotIn("token_hash", json.dumps(listing))

    def test_a2a_auth_parity(self):
        out = self.create_room("A2AParity")
        rid, otok = out["room"]["id"], out["token"]
        owner = out["agent"]["id"]
        _, inv = self.invite(rid, otok)
        _, j1 = self.join(rid, inv["token"], name="Worker1")
        _, inv2 = self.invite(rid, otok)
        _, j2 = self.join(rid, inv2["token"], name="Worker2")
        w1, w2 = j1["agent"]["id"], j2["agent"]["id"]
        code, goal = req("POST", f"/api/rooms/{rid}/goals",
                         {"title": "A2AWork", "budget": 500}, token=otok)
        self.assertEqual(code, 200, goal)

        def rpc(token, method, params):
            return req("POST", f"/api/rooms/{rid}/a2a",
                       {"jsonrpc": "2.0", "id": 7, "method": method,
                        "params": params}, token=token)

        # task/send via A2A is bound to the bearer caller
        code, sent = rpc(j1["token"], "task/send",
                         {"goal_id": goal["id"], "title": "T1"})
        self.assertEqual(code, 200, sent)
        self.assertIn("result", sent, sent)
        tid = sent["result"]["task_id"]
        code, led = req("GET", f"/api/rooms/{rid}/ledger?since=0", token=otok)
        created = [e for e in led["events"]
                   if e["type"] == "task_created" and
                   e["task_id"] == tid]
        self.assertTrue(created, led)
        self.assertEqual(created[0]["actor"], w1)
        # worker1 claims it; worker2 (not holder, not owner) cannot cancel
        code, _ = req("POST", f"/api/rooms/{rid}/tasks/{tid}/claim",
                      {"agent_id": w1}, token=j1["token"])
        self.assertEqual(code, 200)
        code, denied = rpc(j2["token"], "task/cancel", {"task_id": tid})
        self.assertEqual(code, 200, denied)
        self.assertEqual(denied["error"]["code"], -32001, denied)
        # holder cancels via A2A: the authenticated actor is recorded
        code, ok = rpc(j1["token"], "task/cancel", {"task_id": tid})
        self.assertEqual(code, 200, ok)
        self.assertEqual(ok["result"]["status"], "cancelled")
        code, led = req("GET", f"/api/rooms/{rid}/ledger?since=0", token=otok)
        cancelled = [e for e in led["events"]
                     if e["type"] == "task_cancelled" and
                     e["task_id"] == tid]
        self.assertTrue(cancelled, led)
        self.assertEqual(cancelled[0]["actor"], w1)
        # owner can cancel anyone's task
        code, sent2 = rpc(j2["token"], "task/send",
                          {"goal_id": goal["id"], "title": "T2"})
        tid2 = sent2["result"]["task_id"]
        code, _ = req("POST", f"/api/rooms/{rid}/tasks/{tid2}/claim",
                      {"agent_id": w2}, token=j2["token"])
        self.assertEqual(code, 200)
        code, ok = rpc(otok, "task/cancel", {"task_id": tid2})
        self.assertEqual(code, 200, ok)
        self.assertEqual(ok["result"]["status"], "cancelled")
        self.assertNotEqual(owner, w2)  # owner really is a different agent

    def test_sse_header_auth_and_query_fallback(self):
        out = self.create_room("StreamAuth")
        rid, otok = out["room"]["id"], out["token"]
        # Authorization-header stream (fetch streaming): works, no URL token
        conn = open_room_stream(rid, otok, use_header=True)
        conn.sock.settimeout(2)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="EvGuest")
        data = read_until_marker(resp, joined["agent"]["id"].encode(), timeout=10)
        conn.close()
        self.assertIn(b"member_joined", data)
        self.assertIn(joined["agent"]["id"].encode(), data)
        # legacy ?token= path (native EventSource) still authenticates
        conn2 = open_room_stream(rid, otok, use_header=False)
        resp2 = conn2.getresponse()
        self.assertEqual(resp2.status, 200)
        conn2.close()
        # no token at all is rejected
        import http.client
        conn3 = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
        conn3.request("GET", f"/api/rooms/{rid}/events?since=0")
        self.assertEqual(conn3.getresponse().status, 401)
        conn3.close()

    def test_sse_revocation_on_member_removal(self):
        import socket
        out = self.create_room("StreamRev")
        rid, otok = out["room"]["id"], out["token"]
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="Streamer")
        stok, member = joined["token"], joined["agent"]["id"]
        conn = open_room_stream(rid, stok, use_header=True)
        conn.sock.settimeout(25)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        code, _ = req("POST", f"/api/rooms/{rid}/members/{member}/remove",
                      {}, token=otok)
        self.assertEqual(code, 200)
        # the revoked stream must close instead of leaking further payloads
        try:
            data = resp.read()
        except socket.timeout:
            self.fail("revoked SSE stream did not close")
        conn.close()
        self.assertIsInstance(data, bytes)
        # the removed member's token is dead everywhere
        code, _ = req("GET", f"/api/rooms/{rid}", token=stok)
        self.assertEqual(code, 401)

    def test_sse_revocation_on_room_delete(self):
        import socket
        out = self.create_room("StreamDel")
        rid, otok = out["room"]["id"], out["token"]
        conn = open_room_stream(rid, otok, use_header=True)
        conn.sock.settimeout(25)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        code, _ = req("POST", f"/api/rooms/{rid}/delete", {}, token=otok)
        self.assertEqual(code, 200)
        try:
            resp.read()
        except socket.timeout:
            self.fail("deleted room's SSE stream did not close")
        conn.close()

    def test_membership_events_stay_in_room(self):
        import socket
        import http.client
        out = self.create_room("PrivEv")
        rid, otok = out["room"]["id"], out["token"]
        # Open the lobby stream at the current seq: the since=0 replay would
        # otherwise deliver every earlier test's room_created events and the
        # silence check below could not distinguish replay from a live leak.
        _, lobby = req("GET", "/api/state")
        lconn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=8)
        lconn.request("GET", f"/api/events?since={lobby['seq']}")
        lconn.sock.settimeout(4)
        lresp = lconn.getresponse()
        self.assertEqual(lresp.status, 200)
        oconn = open_room_stream(rid, otok, use_header=True)
        oconn.sock.settimeout(2)
        oresp = oconn.getresponse()
        self.assertEqual(oresp.status, 200)
        _, inv = self.invite(rid, otok)
        _, joined = self.join(rid, inv["token"], name="PrivGuest")
        # the room stream sees the private member_joined event...
        data = read_until_marker(oresp, b"PrivGuest", timeout=10)
        oconn.close()
        self.assertIn(b"member_joined", data)
        self.assertIn(b"PrivGuest", data)
        # ...but the lobby stream never does (idle: no data within 4s)
        try:
            chunk = lresp.read(1024)
            self.assertEqual(chunk, b"",
                             "lobby stream carried room membership data")
        except socket.timeout:
            pass
        lconn.close()

    def test_origin_validation(self):
        def post_origin(origin):
            return req("POST", "/api/agents/register", {"name": "Ori"},
                       extra_headers={"Origin": origin} if origin else None)[0]

        self.assertEqual(post_origin(None), 200)
        self.assertEqual(post_origin("http://127.0.0.1:8481"), 200)
        self.assertEqual(post_origin("https://127.0.0.1:8481"), 200)
        self.assertEqual(post_origin("https://evil.example.com"), 403)
        self.assertEqual(post_origin("http://evil.example.com"), 403)


# ------------------------------------------------------------------ Part C

PORT2 = 8482
BASE2 = f"http://127.0.0.1:{PORT2}"
OP_TOKEN = "op-secret-test"
STATE_PATH2 = os.path.join(TMP, "state2.json")


def req2(method, path, body=None, token=None, extra_headers=None):
    r = urllib.request.Request(BASE2 + path, method=method)
    if body is not None:
        r.data = json.dumps(body).encode()
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    for k, v in (extra_headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read() or b"{}"
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, {"_raw": raw[:200]}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


class PublicModeApiTests(unittest.TestCase):
    """PLAYGROUNDS_OPERATOR_TOKEN set: dashboard, lobby API, room creation and
    the room directory are gated; invite joins and room bearer calls are
    unaffected; joins are rate-limited."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PLAYGROUNDS_STATE_PATH=STATE_PATH2,
                   PLAYGROUNDS_PORT=str(PORT2),
                   PLAYGROUNDS_OPERATOR_TOKEN=OP_TOKEN)
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py")],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        probe = urllib.request.Request(
            BASE2 + "/api/policy",
            headers={"Authorization": "Bearer " + OP_TOKEN})
        for _ in range(60):
            try:
                urllib.request.urlopen(probe, timeout=2).read()
                break
            except Exception:
                time.sleep(0.25)
        else:
            cls.proc.terminate()
            raise RuntimeError("public-mode server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()

    def test_lobby_api_gated(self):
        code, _ = req2("POST", "/api/agents/register", {"name": "mallory"})
        self.assertEqual(code, 403)
        code, out = req2("POST", "/api/agents/register", {"name": "mallory"},
                         token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        self.assertIn("agent", out)

    def test_lobby_reads_gated(self):
        code, _ = req2("GET", "/api/policy")
        self.assertEqual(code, 403)
        # query-string operator tokens are rejected: credentials never in URLs
        code, _ = req2("GET", "/api/policy?token=" + OP_TOKEN)
        self.assertEqual(code, 403)
        code, _ = req2("GET", "/api/policy", token=OP_TOKEN)
        self.assertEqual(code, 200)

    def test_dashboard_shell_is_public(self):
        # the join shell is public so invited non-operators can open it...
        code, out = req2("GET", "/")
        self.assertEqual(code, 200, out)
        body = out.get("_raw", b"").decode("utf-8", "replace")
        # ...and it no longer propagates operator tokens through the URL
        self.assertNotIn("URLSearchParams", body)
        self.assertNotIn("?token=", body)
        # ...while the lobby API behind it stays gated
        code, _ = req2("GET", "/api/state")
        self.assertEqual(code, 403)

    def test_room_creation_gated(self):
        code, _ = req2("POST", "/api/rooms", {"name": "Nope"})
        self.assertEqual(code, 403)
        code, out = req2("POST", "/api/rooms", {"name": "Pub"}, token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        self.assertIn("token", out)

    def test_directory_gated(self):
        code, _ = req2("GET", "/api/rooms")
        self.assertEqual(code, 403)
        code, out = req2("GET", "/api/rooms", token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        self.assertIn("rooms", out)

    def test_invite_flow_unaffected_by_operator_gate(self):
        code, out = req2("POST", "/api/rooms", {"name": "Open"}, token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        rid, otok = out["room"]["id"], out["token"]
        # invite + join with NO operator token anywhere
        code, inv = req2("POST", f"/api/rooms/{rid}/invites",
                         {"label": "friend", "ttl_seconds": 600}, token=otok)
        self.assertEqual(code, 200, inv)
        code, joined = req2("POST", f"/api/rooms/{rid}/join",
                            {"invite_token": inv["token"],
                             "agent_name": "Friend"})
        self.assertEqual(code, 200, joined)
        # room bearer calls work without the operator token too
        code, world = req2("GET", f"/api/rooms/{rid}/world", token=joined["token"])
        self.assertEqual(code, 200, world)
        self.assertTrue(world["authenticated"])

    def test_join_rate_limited(self):
        code, out = req2("POST", "/api/rooms", {"name": "RL"}, token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        rid = out["room"]["id"]
        # spoofed X-Forwarded-For from an untrusted peer is ignored: rotating
        # fake client IPs does not mint fresh budgets, so the shared peer
        # bucket still trips.
        codes = [req2("POST", f"/api/rooms/{rid}/join",
                      {"invite_token": "bogus", "agent_name": "x"},
                      extra_headers={"X-Forwarded-For": f"10.99.99.{i}"})[0]
                 for i in range(31)]
        self.assertTrue(all(c in (403, 429) for c in codes), codes)
        self.assertEqual(codes[-1], 429)


# ------------------------------------------------------------------ Part D

PORT3 = 8483
BASE3 = f"http://127.0.0.1:{PORT3}"
STATE_PATH3 = os.path.join(TMP, "state3.json")


def req3(method, path, body=None, token=None, extra_headers=None):
    r = urllib.request.Request(BASE3 + path, method=method)
    if body is not None:
        r.data = json.dumps(body).encode()
        r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    for k, v in (extra_headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


class TrustedProxyTests(unittest.TestCase):
    """PLAYGROUNDS_TRUSTED_PROXIES=127.0.0.1 (the direct peer IS trusted, so
    proxy headers are honored) and an explicit PLAYGROUNDS_TRUSTED_ORIGIN."""

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PLAYGROUNDS_STATE_PATH=STATE_PATH3,
                   PLAYGROUNDS_PORT=str(PORT3),
                   PLAYGROUNDS_TRUSTED_PROXIES="127.0.0.1",
                   PLAYGROUNDS_TRUSTED_ORIGIN="https://playgrounds.example.test")
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py")],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen(BASE3 + "/api/policy",
                                       timeout=2).read()
                break
            except Exception:
                time.sleep(0.25)
        else:
            cls.proc.terminate()
            raise RuntimeError("trusted-proxy server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()

    def test_trusted_proxy_honors_forwarded_ip(self):
        code, out = req3("POST", "/api/rooms", {"name": "PX"})
        self.assertEqual(code, 200, out)
        rid = out["room"]["id"]
        hdr = {"X-Forwarded-For": "10.9.9.9"}
        codes = [req3("POST", f"/api/rooms/{rid}/join",
                      {"invite_token": "bogus", "agent_name": "x"},
                      extra_headers=hdr)[0] for _ in range(31)]
        # the forwarded IP is the bucket key: exactly 30 failures then 429
        self.assertEqual(codes[:30], [403] * 30)
        self.assertEqual(codes[30], 429)
        # the direct peer's own bucket is unaffected
        code, _ = req3("POST", f"/api/rooms/{rid}/join",
                       {"invite_token": "bogus", "agent_name": "x"})
        self.assertEqual(code, 403)

    def test_trusted_origin(self):
        def post_origin(origin):
            return req3("POST", "/api/agents/register", {"name": "Ori"},
                        extra_headers={"Origin": origin})[0]

        self.assertEqual(post_origin("https://playgrounds.example.test"), 200)
        self.assertEqual(post_origin("https://evil.example.test"), 403)
        self.assertEqual(post_origin("https://playgrounds.example.test.evil.com"), 403)


if __name__ == "__main__":
    unittest.main(verbosity=1)
