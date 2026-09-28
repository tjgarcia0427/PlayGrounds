"""Fail-closed verifier identity, through helper and HTTP boundaries."""
import copy
import unittest
import test_v02 as baseline
from test_v02 import srv, reset_state, mk_agent, mk_goal, mk_task, http

class Identity(unittest.TestCase):
    def setUp(self):
        reset_state(); mk_goal(); mk_agent("worker"); mk_agent("reviewer")
        mk_task(status="pending_verification", agent_id="worker", result="done", bounty=40, escrow=40)
        srv.state["goals"]["goal_1"]["budget_available"] = 960

    def test_invalid_identity_never_mutates_or_pays(self):
        for identity in (None, "", " ", False, [], {}, "worker", "unknown"):
            for approved in (True, False):
                with self.subTest(identity=identity, approved=approved):
                    before = copy.deepcopy(srv.state)
                    response = srv.verify_task("task_1", approved, verifier_agent_id=identity)
                    self.assertIn(response.get("code"), (400, 403, 404))
                    self.assertEqual(before, srv.state)

    def test_identityless_cached_approval_not_replayed(self):
        srv.record_idempotency("old", {"task": {"status": "done"}})
        self.assertEqual(srv.verify_task("task_1", True, idempotency_key="old")["code"], 400)

    def test_named_independent_reviewer_settles(self):
        result = srv.verify_task("task_1", True, verifier_agent_id="reviewer")
        self.assertEqual(result["verification_receipt"]["verifier"], {"type": "agent", "id": "reviewer"})
        self.assertEqual(srv.state["agents"]["worker"]["credits"], 36)

class HTTPIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.Integration.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):
        baseline.Integration.tearDownClass.__func__(cls)
    def test_omitted_rest_identity_cannot_self_approve(self):
        _, worker = http("POST", "/api/agents/register", {"name": "worker"})
        _, reviewer = http("POST", "/api/agents/register", {"name": "reviewer"})
        _, goal = http("POST", "/api/goals", {"title": "Identity", "budget": 40})
        _, task = http("POST", f"/api/goals/{goal['id']}/tasks", {"title": "work", "bounty": 40})
        path = f"/api/tasks/{task['id']}"
        self.assertEqual(http("POST", path + "/claim", {"agent_id": worker["id"]})[0], 200)
        self.assertEqual(http("POST", path + "/complete", {"agent_id": worker["id"], "result": "done"})[0], 200)
        for payload in ({"approved": True}, {"approved": True, "verifier_agent_id": worker["id"]}):
            self.assertIn(http("POST", path + "/verify", payload)[0], (400, 403))
        state = http("GET", "/api/state")[1]
        self.assertEqual(state["tasks"][task["id"]]["status"], "pending_verification")
        self.assertEqual(state["agents"][worker["id"]]["credits"], 0)
        self.assertEqual(http("POST", path + "/verify", {"approved": True, "verifier_agent_id": reviewer["id"]})[0], 200)

if __name__ == "__main__":
    unittest.main(verbosity=2)
