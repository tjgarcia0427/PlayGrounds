#!/usr/bin/env python3
"""Playgrounds v0.2 test suite.

Part A — unit tests: import server.py against an isolated temp state file and
exercise migration, ledger chain, topology selection, plans, idempotency,
reputation deadband, settlement math, and verification receipts.

Part B — integration tests: boot a real server on 127.0.0.1:8479 with a temp
state file and drive the HTTP API end to end (4-agent cap, full task
lifecycle, A2A round trip, static avatars, SSE).

Usage: python3 test_v02.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="playgrounds-v02-test-")
STATE_PATH = os.path.join(TMP, "state.json")
os.environ["PLAYGROUNDS_STATE_PATH"] = STATE_PATH

sys.path.insert(0, HERE)
import server as srv  # noqa: E402  (imports against the temp state file)


def reset_state():
    srv.state.clear()
    srv.state.update(srv.blank_state())
    srv.save_state()


def mk_agent(aid="agent_1", name="Ada", caps=("coding",), model="claude-opus-4-1"):
    srv.state["agents"][aid] = {
        "id": aid, "name": name, "avatar": "🤖", "color": "#7c6cf0",
        "plush": "plush1.png", "capabilities": list(caps),
        "model": model, "model_tier": srv.model_tier(model),
        "agent_card": {}, "scopes": ["*"], "tenant_id": "local",
        "observed": {"tasks": 0, "verified": 0, "quality_sum": 0.0,
                     "latency_sum": 0.0, "cost_sum": 0.0},
        "credits": 0, "status": "idle", "current_task": None,
        "last_heartbeat": srv.utcnow()}
    srv.state["agent_stats"][aid] = srv.blank_agent_stats()
    return srv.state["agents"][aid]


def mk_goal(gid="goal_1", budget=1000):
    srv.state["goals"][gid] = {
        "id": gid, "title": "Test goal", "description": "", "budget": budget,
        "budget_available": budget, "budget_spent": 0, "tenant_id": "local",
        "review_pool_pct": 0.10, "plan_ids": [], "created_at": srv.utcnow()}
    return srv.state["goals"][gid]


def mk_task(tid="task_1", gid="goal_1", bounty=30, status="open", **kw):
    t = {"id": tid, "goal_id": gid, "plan_id": None, "title": "Test task",
         "status": status, "agent_id": None, "result": None, "bounty": bounty,
         "required_capabilities": [], "effort": 3, "task_type": "general",
         "dependencies": [], "success_criteria": "done", "risk": "low",
         "decomposability": 0.3, "coupling": 0.7,
         "input_contract": {}, "output_contract": {},
         "topology": "solo", "task_version": 1, "artifact_ids": [],
         "progress": [],
         "lease": {"holder": None, "expires": 0, "last_progress_at": 0},
         "stall_count": 0, "verification_receipt": None,
         "settlement_receipt": None, "escrow": 0, "rejections": 0,
         "created_at": srv.utcnow(), "claimed_at": None, "claim_expires": 0,
         "completed_at": None, "verified_at": None}
    t.update(kw)
    srv.state["tasks"][tid] = t
    return t


class Unit(unittest.TestCase):
    def setUp(self):
        reset_state()

    # ---- migration ----
    def test_migration_v01_state(self):
        v01 = {"agents": {"a1": {"id": "a1", "name": "Old", "credits": 5,
                                 "status": "idle", "capabilities": ["coding"],
                                 "model": "gpt-4o-mini"}},
               "goals": {"g1": {"id": "g1", "title": "G", "budget": 100,
                                 "budget_available": 100}},
               "tasks": {"t1": {"id": "t1", "goal_id": "g1", "title": "T",
                                 "status": "open", "bounty": 10}},
               "ledger": [{"seq": 1, "ts": 1.0, "type": "x", "actor": "s",
                            "data": {}}],
               "seq": 9}
        bak_path = os.path.join(TMP, "mig.json")
        with open(bak_path, "w") as f:
            json.dump(v01, f)
        old_path, old_state = srv.STATE_PATH, srv.state
        try:
            srv.STATE_PATH = bak_path
            srv.state.clear()
            srv.state.update(json.load(open(bak_path)))
            srv.migrate_state()
            self.assertEqual(srv.state["schema_version"], 2)
            self.assertTrue(os.path.exists(bak_path + ".v01.bak"))
            a = srv.state["agents"]["a1"]
            self.assertEqual(a["plush"], "plush1.png")
            self.assertIn("agent_card", a)
            self.assertIn("observed", a)
            t = srv.state["tasks"]["t1"]
            self.assertEqual(t["topology"], "solo")
            self.assertEqual(t["task_version"], 1)
            ok, failing = srv.verify_ledger_chain()
            self.assertTrue(ok, f"chain broken at {failing}")
        finally:
            srv.STATE_PATH, srv.state = old_path, old_state

    # ---- ledger ----
    def test_ledger_chain_and_tamper(self):
        mk_goal()
        with srv.lock:
            srv.ledger_append("a", {"x": 1}, actor="t", goal_id="goal_1")
            srv.ledger_append("b", {"x": 2}, actor="t", goal_id="goal_1")
        ok, _ = srv.verify_ledger_chain()
        self.assertTrue(ok)
        d1 = srv.ledger_digest()
        srv.state["ledger"][-1]["data"]["x"] = 999
        ok, failing = srv.verify_ledger_chain()
        self.assertFalse(ok)
        self.assertIsNotNone(failing)
        self.assertNotEqual(d1, srv.ledger_digest())

    # ---- topology ----
    def test_topology_solo_default(self):
        mk_goal()
        mk_agent()
        t = mk_task(success_criteria="tests pass", risk="low")
        d = srv.select_topology(t)
        self.assertEqual(d["output"]["topology"], "solo")
        self.assertEqual(srv.state["tasks"]["task_1"]["topology"], "solo")

    def test_topology_needs_input(self):
        mk_goal()
        # effort>=4 with no success criteria: orchestrator must ask, not guess
        t = mk_task(success_criteria="", risk="high", bounty=200, effort=5)
        orch = srv.orchestrate_task(t)
        self.assertEqual(orch["status"], "needs_input")
        self.assertEqual(srv.state["tasks"]["task_1"]["status"], "needs_input")

    def test_topology_team_when_justified(self):
        mk_goal()
        for i in range(4):
            mk_agent(aid=f"agent_{i}", name=f"A{i}",
                     caps=("coding", "review"), model="claude-opus-4-1")
        t = mk_task(success_criteria="ship it", risk="medium", bounty=300,
                    decomposability=0.9, coupling=0.1, effort=5,
                    required_capabilities=["coding", "review"])
        d = srv.select_topology(t)
        self.assertIn(d["output"]["topology"], ("sealed_scouts", "specialist_dag"))
        self.assertTrue(2 <= d["output"]["team_size"] <= 4)

    # ---- plans ----
    def test_plan_and_replan(self):
        mk_goal()
        p = srv.create_plan("goal_1", "Win", "done", actor="human")
        self.assertEqual(p["version"], 1)
        p2 = srv.replan(p["id"], "scope changed", actor="human")
        self.assertEqual(p2["version"], 2)
        self.assertEqual(len(p2["history"]), 1)
        self.assertEqual(p2["history"][0]["version"], 2)
        self.assertEqual(p2["history"][0]["reason"], "scope changed")

    # ---- idempotency ----
    def test_idempotency_roundtrip(self):
        with srv.lock:
            self.assertIsNone(srv.check_idempotency("k1"))
            srv.record_idempotency("k1", {"v": 42})
        dup = srv.check_idempotency("k1")
        self.assertEqual(dup["v"], 42)
        self.assertTrue(dup["deduplicated"])

    # ---- reputation deadband ----
    def test_reputation_deadband(self):
        mk_agent()
        # neutral middle: recorded, not moved
        moved = srv.update_reputation("agent_1", ["coding"], 0.5, 0.5)
        self.assertEqual(moved, [])
        post = srv.state["reputation"]["agent_1"]["coding"]
        self.assertEqual(post["alpha"], 2.0)
        self.assertEqual(post["neutral"], 1)
        # high-confidence high quality: positive
        moved = srv.update_reputation("agent_1", ["coding"], 0.9, 0.9)
        self.assertEqual(moved, ["coding"])
        self.assertGreater(srv.state["reputation"]["agent_1"]["coding"]["alpha"], 2.0)
        # high-confidence low quality: negative
        moved = srv.update_reputation("agent_1", ["coding"], 0.2, 0.9)
        self.assertEqual(moved, ["coding"])
        post = srv.state["reputation"]["agent_1"]["coding"]
        self.assertGreater(post["beta"], 2.0)
        # low confidence high quality: neutral (no move)
        a0 = post["alpha"]
        moved = srv.update_reputation("agent_1", ["coding"], 0.95, 0.4)
        self.assertEqual(moved, [])
        self.assertEqual(srv.state["reputation"]["agent_1"]["coding"]["alpha"], a0)
        view = srv.reputation_view("agent_1")
        self.assertIn("coding", view)
        self.assertIn("mean", view["coding"])

    # ---- settlement math ----
    def test_marginal_shares_sum_and_escrow(self):
        mk_goal()
        mk_agent("agent_1")
        mk_agent("agent_2")
        t = mk_task(bounty=100, status="claimed", agent_id="agent_1",
                    escrow=100, artifact_ids=[])
        shares = srv.marginal_shares(t, {})
        total = round(sum(s["marginal"] for s in shares), 6)
        self.assertAlmostEqual(total, 1.0, places=5)
        self.assertTrue(all(s["marginal"] >= 0 for s in shares))

    def test_verify_legacy_pays_worker_full(self):
        mk_goal()
        mk_agent()
        t = mk_task(bounty=30, status="pending_verification", agent_id="agent_1",
                    escrow=30, result="done", claimed_at=srv.utcnow() - 10,
                    completed_at=srv.utcnow())
        srv.state["goals"]["goal_1"]["budget_available"] = 970
        res = srv.verify_task("task_1", True, approved_credits=30)
        self.assertNotIn("error", res)
        self.assertEqual(srv.state["agents"]["agent_1"]["credits"], 30)
        self.assertEqual(res["task"]["status"], "done")

    def test_verify_v02_settlement_and_receipt(self):
        mk_goal()
        mk_agent("agent_1")
        mk_agent("agent_2", name="Rex")
        t = mk_task(bounty=100, status="pending_verification",
                    agent_id="agent_1", escrow=100, result="shipped",
                    claimed_at=srv.utcnow() - 60, completed_at=srv.utcnow())
        srv.state["goals"]["goal_1"]["budget_available"] = 900
        res = srv.verify_task("task_1", True, verifier_agent_id="agent_2",
                              quality=0.9, confidence=0.9)
        self.assertNotIn("error", res)
        vr = res["verification_receipt"]
        self.assertEqual(vr["decision"], "accepted")
        self.assertTrue(vr["verification_id"].startswith("ver_"))
        self.assertTrue(vr["signature"].startswith("stub:"))
        st = res["settlement_receipt"]
        paid = sum(st["payouts"].values()) + st["reviewer_paid"] \
            + st["leftover_to_budget"]
        self.assertAlmostEqual(paid, 100.0, places=1)
        # reviewer got the 10% review pool
        self.assertAlmostEqual(st["reviewer_paid"], 10.0, places=1)
        self.assertAlmostEqual(srv.state["agents"]["agent_2"]["credits"],
                               10.0, places=1)

    def test_verify_self_review_rejected(self):
        mk_goal()
        mk_agent()
        mk_task(bounty=10, status="pending_verification", agent_id="agent_1",
                escrow=10, result="x")
        res = srv.verify_task("task_1", True, verifier_agent_id="agent_1",
                              quality=0.9, confidence=0.9)
        self.assertEqual(res.get("code"), 403)

    def test_verify_rejection_returns_escrow(self):
        mk_goal()
        mk_agent()
        mk_task(bounty=40, status="pending_verification", agent_id="agent_1",
                escrow=40, result="bad")
        srv.state["goals"]["goal_1"]["budget_available"] = 960
        res = srv.verify_task("task_1", False, quality=0.2, confidence=0.9)
        self.assertEqual(res["task"]["status"], "open")
        self.assertEqual(srv.state["goals"]["goal_1"]["budget_available"], 1000)
        self.assertEqual(srv.state["agents"]["agent_1"]["credits"], 0)

    def test_deterministic_checks_blocking(self):
        mk_goal()
        # missing result -> blocking fail
        t = mk_task(result=None)
        checks = srv.run_deterministic_checks(t)
        blocking = [c for c in checks
                    if c["result"] == "fail" and c.get("blocking")]
        self.assertTrue(blocking)
        # contract field missing -> non-blocking fail (judgment call)
        t2 = mk_task(result="short",
                     output_contract={"required_fields": ["tests pass"]})
        checks2 = srv.run_deterministic_checks(t2)
        cf = [c for c in checks2 if c["id"] == "contract_fields"][0]
        self.assertEqual(cf["result"], "fail")
        self.assertFalse(cf["blocking"])

    # ---- agent card ----
    def test_agent_card_declared_vs_observed(self):
        a = mk_agent()
        card = srv.build_agent_card(a)
        self.assertIn("skills", card)      # declared claims
        self.assertIn("observed", card)    # separate measured history
        self.assertIn("disclaimer", card["observed"])
        self.assertEqual(card["version"], "0.2.0")

    def test_playground_card(self):
        mk_agent()
        card = srv.playground_card()
        self.assertEqual(card["protocol"], "playgrounds-jsonrpc/0.2")
        self.assertEqual(card["maxAgents"], 4)
        self.assertEqual(card["registeredAgents"], 1)


# ------------------------- Part B: integration -------------------------

def http(method, path, data=None, port=8479):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", method=method,
        data=None if method == "GET" else json.dumps(data or {}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            return r.status, (json.loads(raw) if "json" in ctype else raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ, PLAYGROUNDS_STATE_PATH=os.path.join(TMP, "int.json"),
                   PLAYGROUNDS_PORT="8479")
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "server.py")],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for _ in range(100):
            try:
                code, _ = http("GET", "/api/policy")
                if code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.2)
        else:
            cls.proc.terminate()
            raise RuntimeError("test server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def test_01_agent_cap_409(self):
        ids = []
        for i in range(4):
            code, res = http("POST", "/api/agents/register",
                             {"name": f"Bot{i}", "capabilities": ["coding"],
                              "model": "gpt-4o-mini"})
            self.assertEqual(code, 200, res)
            ids.append(res["id"])
            self.assertTrue(res["agent"]["plush"].startswith("plush"))
        code, res = http("POST", "/api/agents/register", {"name": "Bot4"})
        self.assertEqual(code, 409)
        self.assertEqual(res["max_agents"], 4)
        self.__class__.agents = ids

    def test_02_full_lifecycle(self):
        a0, a1 = self.agents[0], self.agents[1]
        code, goal = http("POST", "/api/goals",
                          {"title": "Ship v0.2", "budget": 500})
        self.assertEqual(code, 200)
        gid = goal["id"]
        code, plan = http("POST", f"/api/goals/{gid}/plans",
                          {"objective": "Build it", "success_criteria": "tests pass"})
        self.assertEqual(code, 200)
        self.assertEqual(plan["version"], 1)
        code, task = http("POST", f"/api/goals/{gid}/tasks",
                          {"title": "Write tests", "bounty": 100,
                           "required_capabilities": ["coding"],
                           "success_criteria": "all tests green",
                           "plan_id": plan["id"]})
        self.assertEqual(code, 200)
        tid = task["id"]
        self.assertEqual(task["topology"], "solo")
        # suggest + route endpoints
        code, sug = http("GET", f"/api/tasks/{tid}/suggest")
        self.assertEqual(code, 200)
        self.assertTrue(sug["suggestions"])
        code, route = http("GET", f"/api/tasks/{tid}/route")
        self.assertEqual(code, 200)
        self.assertEqual(route["routing"]["mode"], "shadow")
        # claim with idempotency
        code, c1 = http("POST", f"/api/tasks/{tid}/claim",
                        {"agent_id": a0, "idempotency_key": "claim-1"})
        self.assertEqual(code, 200)
        code, c2 = http("POST", f"/api/tasks/{tid}/claim",
                        {"agent_id": a0, "idempotency_key": "claim-1"})
        self.assertEqual(code, 200)
        self.assertTrue(c2.get("deduplicated"))
        # progress
        code, pr = http("POST", f"/api/tasks/{tid}/progress",
                        {"agent_id": a0, "note": "halfway",
                         "progress_pct": 0.5})
        self.assertEqual(code, 200)
        # artifact
        code, art = http("POST", f"/api/tasks/{tid}/artifacts",
                         {"agent_id": a0, "kind": "result", "name": "tests.py",
                          "content": "assert True"})
        self.assertEqual(code, 200)
        self.assertTrue(art["artifact"]["digest"].startswith("sha256:"))
        # complete
        code, done = http("POST", f"/api/tasks/{tid}/complete",
                          {"agent_id": a0, "result": "all tests green"})
        self.assertEqual(code, 200)
        self.assertEqual(done["task"]["status"], "pending_verification")
        # verify v0.2 style with independent reviewer
        code, ver = http("POST", f"/api/tasks/{tid}/verify",
                         {"approved": True, "verifier_agent_id": a1,
                          "quality": 0.9, "confidence": 0.9})
        self.assertEqual(code, 200)
        self.assertEqual(ver["task"]["status"], "done")
        st = ver["settlement_receipt"]
        total = sum(st["payouts"].values()) + st["reviewer_paid"] \
            + st["leftover_to_budget"]
        self.assertAlmostEqual(total, 100.0, places=1)
        # reputation moved for the worker
        code, rep = http("GET", f"/api/agents/{a0}/reputation")
        self.assertEqual(code, 200)
        self.assertIn("coding", rep["reputation"])
        # ledger has the full trail with a valid chain
        code, led = http("GET", "/api/ledger")
        self.assertEqual(code, 200)
        types = {e["type"] for e in led["events"]}
        for want in ("task_created", "task_leased", "progress_recorded",
                     "artifact_published", "task_submitted",
                     "verification_issued", "credits_settled"):
            self.assertIn(want, types)
        self.__class__.gid = gid

    def test_03_needs_input_and_clarify(self):
        code, task = http("POST", f"/api/goals/{self.gid}/tasks",
                          {"title": "Do the risky thing", "bounty": 50,
                           "risk": "high", "effort": 5})
        self.assertEqual(code, 200)
        self.assertEqual(task["status"], "needs_input")
        tid = task["id"]
        code, out = http("POST", f"/api/tasks/{tid}/clarify",
                         {"success_criteria": "zero downtime deploy"})
        self.assertEqual(code, 200)
        self.assertEqual(out["status"], "open")

    def test_04_cancel(self):
        code, task = http("POST", f"/api/goals/{self.gid}/tasks",
                          {"title": "Scrap this", "bounty": 20,
                           "success_criteria": "n/a"})
        tid = task["id"]
        code, c = http("POST", f"/api/tasks/{tid}/cancel",
                       {"reason": "no longer needed"})
        self.assertEqual(code, 200)
        self.assertEqual(c["task"]["status"], "cancelled")

    def test_05_a2a_roundtrip(self):
        code, card = http("POST", "/a2a",
                          {"jsonrpc": "2.0", "id": 1, "method": "card/get",
                           "params": {}})
        self.assertEqual(code, 200)
        self.assertEqual(card["result"]["protocol"], "playgrounds-jsonrpc/0.2")
        code, sent = http("POST", "/a2a",
                          {"jsonrpc": "2.0", "id": 2, "method": "task/send",
                           "params": {"goal_id": self.gid,
                                      "title": "A2A task", "bounty": 10,
                                      "success_criteria": "ok"}})
        self.assertEqual(code, 200)
        tid = sent["result"]["task_id"]
        code, got = http("POST", "/a2a",
                         {"jsonrpc": "2.0", "id": 3, "method": "task/get",
                          "params": {"task_id": tid}})
        self.assertEqual(code, 200)
        self.assertEqual(got["result"]["task"]["id"], tid)
        code, cx = http("POST", "/a2a",
                        {"jsonrpc": "2.0", "id": 4, "method": "task/cancel",
                         "params": {"task_id": tid}})
        self.assertEqual(code, 200)
        self.assertEqual(cx["result"]["status"], "cancelled")

    def test_06_wellknown_and_avatars_and_policy(self):
        code, card = http("GET", "/.well-known/agent-card.json")
        self.assertEqual(code, 200)
        self.assertEqual(card["maxAgents"], 4)
        code, pol = http("GET", "/api/policy")
        self.assertEqual(code, 200)
        self.assertEqual(pol["max_agents"], 4)
        code, png = http("GET", "/avatars/plush1.png")
        self.assertEqual(code, 200)
        self.assertTrue(png[:4] == b"\x89PNG")

    def test_07_sse_streams(self):
        import socket
        s = socket.create_connection(("127.0.0.1", 8479), timeout=10)
        s.sendall(b"GET /api/events?since=0 HTTP/1.0\r\nHost: 127.0.0.1:8479\r\n\r\n")
        s.settimeout(5)
        data = s.recv(4096)
        s.close()
        self.assertIn(b"text/event-stream", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
