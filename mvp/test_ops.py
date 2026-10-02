#!/usr/bin/env python3
"""Ops hardening suite (issue #33).

Part A — unit: health_report() payload shape, sensitivity and tamper
detection, against an isolated temp state (in-process).
Part B — integration: boot a real server on 127.0.0.1:8485 with an
operator token; /api/health is operator-gated (header only, never the
query string) and reports a live, verifying ledger.
Part C — backup rotation: timestamped snapshots, keep-N pruning,
restore with a pre-restore safety copy (pure state_backup functions).
Part D — isolated restore demonstration: real room activity on
127.0.0.1:8486 -> snapshot -> wipe state.json -> restore -> reboot;
the ledger digest and room auth must survive the round trip.
Part E — log hygiene: everything the Part B/D servers printed is
scanned for the synthetic credentials used and for credential
patterns; plus a static scan that no print call in server.py or
mcp_server.py touches headers/Authorization/token material.

Usage: python3 test_ops.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="playgrounds-ops-test-")
STATE_A = os.path.join(TMP, "state-a.json")
os.environ["PLAYGROUNDS_STATE_PATH"] = STATE_A

sys.path.insert(0, HERE)
import server as srv  # noqa: E402
import state_backup  # noqa: E402

# Synthetic credentials, unique to this suite so the Part E log scan can
# prove they never reach the server logs. Never real secrets.
OP_TOKEN = "ops-test-" + "synthetic" + "-33"

LOG_DIR = os.path.join(TMP, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
SECRETS_USED = [OP_TOKEN]  # Parts B/D append the tokens they mint


def reset_state():
    srv.state.clear()
    srv.state.update(srv.blank_state())
    srv.save_state()


class Server:
    """A real server subprocess with output captured to a log file."""

    def __init__(self, port, state_path, log_name, extra_env=None):
        self.port = port
        self.base = f"http://127.0.0.1:{port}"
        self.log_path = os.path.join(LOG_DIR, log_name)
        env = dict(os.environ, PLAYGROUNDS_STATE_PATH=state_path,
                   PLAYGROUNDS_PORT=str(port),
                   PLAYGROUNDS_OPERATOR_TOKEN=OP_TOKEN)
        env.update(extra_env or {})
        self._log = open(self.log_path, "ab")
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py")],
            env=env, stdout=self._log, stderr=subprocess.STDOUT)
        for _ in range(60):
            try:
                self.req("GET", "/api/health")
                break
            except urllib.error.HTTPError:
                break  # any HTTP response (403 here) means it is up
            except Exception:
                time.sleep(0.25)
        else:
            self.stop()
            raise RuntimeError(f"server on {port} did not start")

    def req(self, method, path, body=None, token=None):
        r = urllib.request.Request(self.base + path, method=method)
        if body is not None:
            r.data = json.dumps(body).encode()
            r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"{}")
            except Exception:
                return e.code, {}

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self._log.close()


# ------------------------------------------------------------------ Part A

class TestAHealthUnit(unittest.TestCase):
    def setUp(self):
        reset_state()

    def test_health_report_shape_and_no_sensitive_data(self):
        srv.ledger_append("health_probe", {"n": 1}, actor="test")
        with srv.lock:
            report = srv.health_report()
        self.assertEqual(set(report), {
            "status", "ledger_ok", "ledger_failing_seq", "ledger_entries",
            "state_size_bytes", "state_age_seconds", "room_count"})
        self.assertEqual(report["status"], "ok")
        self.assertTrue(report["ledger_ok"])
        self.assertIsNone(report["ledger_failing_seq"])
        self.assertGreaterEqual(report["ledger_entries"], 1)
        self.assertGreater(report["state_size_bytes"], 0)
        self.assertGreaterEqual(report["state_age_seconds"], 0)
        self.assertEqual(report["room_count"], 0)
        blob = json.dumps(report)
        self.assertNotIn(srv.state["server_salt"], blob)
        self.assertNotIn("sha256:", blob)

    def test_health_report_room_count(self):
        srv.state["rooms"]["room_probe"] = srv.blank_room("Probe")
        with srv.lock:
            report = srv.health_report()
        self.assertEqual(report["room_count"], 1)

    def test_health_report_detects_tampered_ledger(self):
        entry = srv.ledger_append("health_probe", {"n": 1}, actor="test")
        srv.state["ledger"][-1]["data"] = {"n": 999}  # tamper, no re-save
        with srv.lock:
            report = srv.health_report()
        self.assertFalse(report["ledger_ok"])
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["ledger_failing_seq"], entry["seq"])


# ------------------------------------------------------------------ Part B

class TestBHealthHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state_path = os.path.join(TMP, "state-b.json")
        cls.server = Server(8485, cls.state_path, "health-server.log")

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_health_requires_operator_header(self):
        code, _ = self.server.req("GET", "/api/health")
        self.assertEqual(code, 403)
        code, _ = self.server.req("GET", "/api/health", token="wrong")
        self.assertEqual(code, 403)
        # credentials never travel in URLs: a query token must not work
        code, _ = self.server.req("GET", f"/api/health?token={OP_TOKEN}")
        self.assertEqual(code, 403)

    def test_health_ok_with_operator_token(self):
        # a mutation first, so the state file exists on disk to measure
        code, out = self.server.req("POST", "/api/rooms",
                                    {"name": "Health Room"}, token=OP_TOKEN)
        self.assertEqual(code, 200, out)
        code, body = self.server.req("GET", "/api/health", token=OP_TOKEN)
        self.assertEqual(code, 200, body)
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["ledger_ok"])
        self.assertEqual(body["room_count"], 1)
        self.assertGreater(body["state_size_bytes"], 0)
        self.assertGreaterEqual(body["state_age_seconds"], 0)
        blob = json.dumps(body)
        self.assertNotIn(OP_TOKEN, blob)
        self.assertNotIn("server_salt", blob)


# ------------------------------------------------------------------ Part C

class TestCBackupRotation(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=TMP)
        self.state = os.path.join(self.dir, "state.json")
        with open(self.state, "w") as f:
            json.dump({"v": 1}, f)

    def test_rotation_keeps_newest_n(self):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(12):
            dest = state_backup.make_snapshot(
                self.state, keep=5, when=base + timedelta(seconds=i))
            self.assertTrue(os.path.exists(dest))
        snaps = state_backup.list_snapshots(self.state)
        self.assertEqual(len(snaps), 5)
        # the survivors are the five newest stamps (seconds 7..11)
        names = [os.path.basename(s) for s in snaps]
        self.assertIn("T000007", names[0])
        self.assertIn("T000011", names[-1])

    def test_snapshot_of_missing_state_is_none(self):
        missing = os.path.join(self.dir, "nope.json")
        self.assertIsNone(state_backup.make_snapshot(missing))

    def test_restore_swaps_content_and_keeps_safety_copy(self):
        snap = state_backup.make_snapshot(self.state)
        with open(self.state, "w") as f:
            json.dump({"v": 2}, f)
        state_backup.restore_snapshot(snap, self.state)
        with open(self.state) as f:
            self.assertEqual(json.load(f), {"v": 1})
        with open(self.state + ".pre-restore") as f:
            self.assertEqual(json.load(f), {"v": 2})


# ------------------------------------------------------------------ Part D

class TestDRestoreDemo(unittest.TestCase):
    """The isolated restore demonstration VISIONQUEST asked for:
    backup -> wipe -> restore -> the ledger verifies and room auth
    still works. Prints its evidence as it goes."""

    def test_full_restore_cycle(self):
        state_path = os.path.join(TMP, "state-d.json")
        server = Server(8486, state_path, "restore-server.log")
        try:
            # Lobby activity first: a full task lifecycle with an
            # independent verifier, so the lobby ledger is non-trivial
            # when its digest is recorded below.
            code, a0 = server.req("POST", "/api/agents/register",
                                  {"name": "DemoWorker",
                                   "capabilities": ["coding"]},
                                  token=OP_TOKEN)
            self.assertEqual(code, 200, a0)
            code, a1 = server.req("POST", "/api/agents/register",
                                  {"name": "DemoVerifier",
                                   "capabilities": ["review"]},
                                  token=OP_TOKEN)
            self.assertEqual(code, 200, a1)
            code, goal = server.req("POST", "/api/goals",
                                    {"title": "Restore demo", "budget": 100},
                                    token=OP_TOKEN)
            self.assertEqual(code, 200, goal)
            code, task = server.req(
                "POST", f"/api/goals/{goal['id']}/tasks",
                {"title": "Survive a restore", "bounty": 10,
                 "required_capabilities": ["coding"]}, token=OP_TOKEN)
            self.assertEqual(code, 200, task)
            tid = task["id"]
            code, _ = server.req("POST", f"/api/tasks/{tid}/claim",
                                 {"agent_id": a0["id"]}, token=OP_TOKEN)
            self.assertEqual(code, 200)
            code, _ = server.req("POST", f"/api/tasks/{tid}/complete",
                                 {"agent_id": a0["id"], "result": "done"},
                                 token=OP_TOKEN)
            self.assertEqual(code, 200)
            code, ver = server.req("POST", f"/api/tasks/{tid}/verify",
                                   {"approved": True,
                                    "verifier_agent_id": a1["id"],
                                    "quality": 0.9, "confidence": 0.9},
                                   token=OP_TOKEN)
            self.assertEqual(code, 200, ver)
            self.assertEqual(ver["task"]["status"], "done")

            # Room activity: room + invite + member join (the room's own
            # ledger gains entries; membership is state-side auth).
            code, out = server.req("POST", "/api/rooms",
                                   {"name": "Restore Room"}, token=OP_TOKEN)
            self.assertEqual(code, 200, out)
            rid, owner_tok = out["room"]["id"], out["token"]
            code, inv = server.req("POST", f"/api/rooms/{rid}/invites",
                                   {"label": "demo"}, token=owner_tok)
            self.assertEqual(code, 200, inv)
            code, joined = server.req(
                "POST", f"/api/rooms/{rid}/join",
                {"invite_token": inv["token"], "name": "DemoMember"})
            self.assertEqual(code, 200, joined)
            member_tok = joined["token"]
            SECRETS_USED.extend([owner_tok, inv["token"], member_tok])

            code, health = server.req("GET", "/api/health", token=OP_TOKEN)
            self.assertEqual(code, 200, health)
            self.assertTrue(health["ledger_ok"])
            self.assertEqual(health["room_count"], 1)
            code, ledger = server.req("GET", "/api/ledger", token=OP_TOKEN)
            self.assertEqual(code, 200, ledger)
            digest_before = ledger["digest"]
            # the digest must cover a real, non-empty lobby ledger —
            # an empty-ledger match would prove nothing
            self.assertGreater(ledger["ledger_seq"], 0)
            self.assertNotEqual(
                digest_before,
                "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
            print(f"[restore-demo] pre-wipe: health={health['status']} "
                  f"rooms={health['room_count']} ledger_seq={ledger['ledger_seq']}")
            print(f"[restore-demo] pre-wipe ledger digest: {digest_before}")
        finally:
            server.stop()

        # Snapshot, wipe, restore.
        snap = state_backup.make_snapshot(state_path)
        self.assertIsNotNone(snap)
        print(f"[restore-demo] snapshot: {os.path.basename(snap)}")
        os.remove(state_path)
        self.assertFalse(os.path.exists(state_path))
        state_backup.restore_snapshot(snap, state_path)
        self.assertTrue(os.path.exists(state_path))
        print("[restore-demo] state.json wiped and restored from snapshot")

        # Reboot on the restored file: chain verifies, digest identical,
        # member auth (state-side) and operator auth (env-side) both work.
        server2 = Server(8486, state_path, "restore-server-2.log")
        try:
            code, health = server2.req("GET", "/api/health", token=OP_TOKEN)
            self.assertEqual(code, 200, health)
            self.assertTrue(health["ledger_ok"], health)
            self.assertEqual(health["room_count"], 1)
            code, ledger = server2.req("GET", "/api/ledger", token=OP_TOKEN)
            self.assertEqual(code, 200, ledger)
            self.assertEqual(ledger["digest"], digest_before)
            code, room_state = server2.req("GET", f"/api/rooms/{rid}/state",
                                           token=member_tok)
            self.assertEqual(code, 200, room_state)
            print(f"[restore-demo] post-restore: health={health['status']} "
                  f"rooms={health['room_count']}")
            print(f"[restore-demo] post-restore ledger digest: "
                  f"{ledger['digest']} (match: {ledger['digest'] == digest_before})")
            print("[restore-demo] member Bearer credential still authenticates "
                  "after restore: /api/rooms/{rid}/state -> 200")
            # the reboot itself took a startup snapshot (rotation is live)
            self.assertGreaterEqual(
                len(state_backup.list_snapshots(state_path)), 2)
        finally:
            server2.stop()


# ------------------------------------------------------------------ Part E

class TestELogHygiene(unittest.TestCase):
    def test_server_logs_contain_no_credentials(self):
        logs = ""
        for name in os.listdir(LOG_DIR):
            with open(os.path.join(LOG_DIR, name), errors="replace") as f:
                logs += f.read()
        self.assertTrue(logs.strip(), "expected captured server output")
        for secret in SECRETS_USED:
            self.assertNotIn(secret, logs)
        self.assertIsNone(re.search(r"Bearer\s+\S{8,}", logs))
        self.assertIsNone(re.search(r"\b(tok|inv)_[A-Za-z0-9_\-]{10,}", logs))
        self.assertIsNone(re.search(r"sha256:[0-9a-f]{64}", logs))

    def test_no_print_call_touches_credentials(self):
        # Static scan: no print/log statement in the server or the MCP
        # connector may reference headers, Authorization, or token values.
        for fname in ("server.py", "mcp_server.py"):
            with open(os.path.join(HERE, fname)) as f:
                for lineno, line in enumerate(f, 1):
                    if "print(" in line or "log_message" in line:
                        for word in ("Authorization", "headers", "token"):
                            self.assertNotIn(
                                word, line,
                                f"{fname}:{lineno} prints {word}: {line.strip()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
