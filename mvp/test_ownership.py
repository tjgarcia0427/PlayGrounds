"""Ownership regression; isolated state via the core test fixtures."""
import copy
import unittest
from test_v02 import srv, reset_state, mk_agent, mk_goal, mk_task

class Ownership(unittest.TestCase):
    def setUp(self):
        reset_state()
        mk_goal()
        for aid in ("worker", "attacker", "reviewer"):
            mk_agent(aid)
        mk_task(status="claimed", agent_id="worker", bounty=40, escrow=40)
        srv.state["goals"]["goal_1"]["budget_available"] = 960

    def test_foreign_publish_rejected_without_mutation_or_bounty_theft(self):
        before = copy.deepcopy(srv.state)
        result = srv.publish_artifact("task_1", "attacker", "result", "stolen", "work", "text/plain")
        self.assertEqual(result.get("code"), 403)
        self.assertEqual(before, srv.state)
        valid = srv.publish_artifact("task_1", "worker", "result", "real", "work", "text/plain")
        self.assertIn("artifact", valid)
        task = srv.state["tasks"]["task_1"]
        task.update(status="pending_verification", result="work")
        result = srv.verify_task("task_1", True, verifier_agent_id="reviewer")
        self.assertEqual(result["task"]["status"], "done")
        self.assertEqual(srv.state["agents"]["attacker"]["credits"], 0)
        self.assertEqual(srv.state["agents"]["worker"]["credits"], 36)
        self.assertEqual(srv.state["agents"]["reviewer"]["credits"], 4)

if __name__ == "__main__":
    unittest.main(verbosity=2)
