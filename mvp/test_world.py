"""Dual-space lifecycle, capacity, social isolation and MCP regressions."""
import copy
import unittest
import world
import mcp_server
import test_v02 as baseline
from test_v02 import srv, reset_state, mk_agent, mk_goal, mk_task, http

class World(unittest.TestCase):
    def setUp(self):
        reset_state(); mk_goal(); mk_agent('a'); mk_agent('r')
        srv.state['agents']['a']['location'] = {'space':'playground', 'goal_id':None}
        srv.state['agents']['a']['social_enabled'] = True

    def test_work_presence_and_return_on_all_terminal_paths(self):
        for status in ('claimed', 'pending_verification'):
            t = mk_task(agent_id='a', status=status, result='done', escrow=10)
            self.assertEqual(world.presence(srv.state,'a')['space'], 'classroom')
            before = copy.deepcopy(srv.state)
            self.assertEqual(world.move(srv.state,'a',{'space':'playground'})['code'],409)
            self.assertEqual(before, srv.state)
        for status in ('done','cancelled','open'):
            t['status'] = status
            self.assertEqual(world.presence(srv.state,'a')['space'], 'playground')

    def test_social_opt_in_rate_limit_bounds_and_separate_history(self):
        srv.state['agents']['a']['social_enabled'] = False
        self.assertEqual(world.post_social(srv.state,{'agent_id':'a','text':'hello'},99)['code'],403)
        srv.state['agents']['a']['social_enabled'] = True
        before = copy.deepcopy(srv.state['messages'])
        self.assertIn('message', world.post_social(srv.state,{'agent_id':'a','text':'hello'},100))
        self.assertEqual(world.post_social(srv.state,{'agent_id':'a','text':'again'},101)['code'],429)
        self.assertEqual(world.post_social(srv.state,{'agent_id':'a','text':'x'*501},103)['code'],400)
        self.assertEqual(world.post_social(srv.state,{'agent_id':'r','text':'hello'},103)['code'],403)
        for i in range(260):
            world.post_social(srv.state,{'agent_id':'a','text':str(i)},104+i*2)
        self.assertEqual(len(srv.state['social_messages']),256)
        self.assertEqual(before,srv.state['messages'])
        mk_task(agent_id='a', status='claimed')
        self.assertEqual(world.post_social(srv.state,{'agent_id':'a','text':'busy'},999)['code'],403)

    def test_move_validation_and_heartbeat_cannot_override_task(self):
        before = copy.deepcopy(srv.state)
        self.assertEqual(world.move(srv.state,'a',{'space':'moon'})['code'],400)
        self.assertEqual(before,srv.state)
        mk_task(agent_id='a',status='claimed')
        srv.state['agents']['a'].update(status='idle',current_task=None)
        self.assertEqual(world.presence(srv.state,'a')['activity'],'working')

    def test_real_review_cancel_and_expiry_return_to_playground(self):
        for outcome in ('approve', 'reject', 'cancel', 'expire'):
            t = mk_task(agent_id='a', status='pending_verification', result='done', escrow=10)
            if outcome in ('approve', 'reject'):
                response = srv.verify_task('task_1', outcome == 'approve', verifier_agent_id='r')
                self.assertNotIn('error', response)
            elif outcome == 'cancel':
                srv.cancel_task('task_1')
            else:
                t.update(status='claimed', lease={'expires':0})
                srv.sweep_expired_claims()
            self.assertEqual(world.presence(srv.state,'a')['space'], 'playground')

    def test_mcp_world_tools_are_dispatchable(self):
        calls=[]
        old=mcp_server.api
        mcp_server.api=lambda *a: calls.append(a) or {'ok':True}
        try:
            for tool,args in [('playgrounds_world',{}),('playgrounds_move',{'agent_id':'a','space':'playground'}),('playgrounds_social_say',{'agent_id':'a','text':'hi'})]:
                self.assertIn(tool,[t['name'] for t in mcp_server.TOOLS])
                self.assertTrue(mcp_server.call_tool(tool,args)['ok'])
        finally: mcp_server.api=old
        self.assertEqual([x[1] for x in calls],['/api/world','/api/agents/a/presence','/api/social'])

class HTTPWorld(unittest.TestCase):
    def setUp(self):
        # Unique state for each scenario, never the pilot's tracked state.
        baseline.Integration.setUpClass.__func__(self)
    def tearDown(self):
        baseline.Integration.tearDownClass.__func__(self)
        import os
        os.unlink(baseline.os.path.join(baseline.TMP,'int.json'))
    def register(self,name):
        code,a=http('POST','/api/agents/register',{'name':name,'space':'playground','social_enabled':True})
        self.assertEqual(code,200)
        return a['id']
    def test_more_than_four_social_agents_and_atomic_classroom_limit(self):
        agents=[self.register(str(i)) for i in range(6)]
        _,g=http('POST','/api/goals',{'budget':100})
        tids=[]
        for i in range(5):
            _,t=http('POST',f"/api/goals/{g['id']}/tasks",{'bounty':10})
            tids.append(t['id'])
            code,_=http('POST',f"/api/tasks/{t['id']}/claim",{'agent_id':agents[i]})
            self.assertEqual(code,200 if i<4 else 409)
        state=http('GET','/api/state')[1]
        self.assertEqual(state['goals'][g['id']]['budget_available'],60)
        self.assertEqual(state['tasks'][tids[-1]]['status'],'open')
        world_state=http('GET','/api/world')[1]
        self.assertEqual(sum(a['presence']['space']=='classroom' for a in world_state['agents']),4)
        self.assertEqual(http('POST',f'/api/agents/{agents[0]}/presence',{'space':'playground'})[0],409)
        http('POST',f'/api/tasks/{tids[0]}/cancel',{})
        self.assertEqual(http('POST',f'/api/tasks/{tids[-1]}/claim',{'agent_id':agents[4]})[0],200)
    def test_classrooms_are_goal_scoped_and_cross_goal_work_is_blocked(self):
        agents=[self.register(str(i)) for i in range(5)]
        for goal_index in range(2):
            _,g=http('POST','/api/goals',{'budget':100})
            for i in range(4 if goal_index == 0 else 1):
                _,t=http('POST',f"/api/goals/{g['id']}/tasks",{'bounty':10})
                aid=agents[i] if goal_index == 0 else agents[4]
                self.assertEqual(http('POST',f"/api/tasks/{t['id']}/claim",{'agent_id':aid})[0],200)
        _,t=http('POST',f"/api/goals/{g['id']}/tasks",{'bounty':10})
        self.assertEqual(http('POST',f"/api/tasks/{t['id']}/claim",{'agent_id':agents[0]})[0],409)

    def test_social_posts_and_presence_survive_reload(self):
        aid=self.register('Social')
        self.assertEqual(http('POST','/api/social',{'agent_id':aid,'text':'Hello classroom! '})[0],200)
        import json
        with open(baseline.os.path.join(baseline.TMP,'int.json')) as f: saved=json.load(f)
        self.assertEqual(saved['agents'][aid]['location']['space'],'playground')
        self.assertEqual(saved['social_messages'][0]['text'],'Hello classroom! ')
        self.assertEqual(saved['messages'],[])
        self.assertEqual(http('POST',f'/api/agents/{aid}/presence',{'space':'classroom'})[0],200)
        self.assertEqual(http('POST','/api/social',{'agent_id':aid,'text':'Nope'})[0],403)

if __name__=='__main__': unittest.main(verbosity=2)
