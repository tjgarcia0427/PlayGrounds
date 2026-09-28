"""Regression coverage for audit findings. Uses only temporary state."""
import hashlib
import json
import unittest
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
import test_v02 as baseline
from test_v02 import srv, reset_state, mk_agent, mk_goal, mk_task, http

class Accounting(unittest.TestCase):
    def setUp(self):
        reset_state()
        mk_goal()
        for aid in ('a', 'b', 'c', 'r'):
            mk_agent(aid)

    def pending(self, amount=100):
        srv.state['goals']['goal_1']['budget_available'] = round(1000-amount, 2)
        return mk_task(status='pending_verification', agent_id='a', escrow=amount, bounty=amount, result='done')

    def test_independent_review_conserves_budget(self):
        self.pending()
        r=srv.verify_task('task_1', True, verifier_agent_id='r')
        g=srv.state['goals']['goal_1']
        self.assertEqual(g['budget_available']+g['budget_spent'], 1000)
        self.assertEqual(g['budget_spent'], 100)

    def test_fractional_split_conserves_cents(self):
        t=self.pending(.05)
        for aid in ('a','b','c'):
            art='art_'+aid
            srv.state['artifacts'][art]={'agent_id':aid,'content':aid,'digest':'sha256:'+hashlib.sha256(aid.encode()).hexdigest()}
            t['artifact_ids'].append(art)
        r=srv.verify_task('task_1',True,verifier_agent_id='r')['settlement_receipt']
        self.assertAlmostEqual(sum(r['payouts'].values())+r['reviewer_paid']+r['leftover_to_budget'],.05,places=8)
        self.assertAlmostEqual(sum(a['credits'] for a in srv.state['agents'].values()), srv.state['goals']['goal_1']['budget_spent'])

    def test_contributor_cannot_review(self):
        t=self.pending()
        srv.state['artifacts']['art']={'agent_id':'b'}
        t['artifact_ids']=['art']
        self.assertEqual(srv.verify_task('task_1',True,verifier_agent_id='b')['code'],403)

    def test_unknown_reviewer_rejected(self):
        self.pending()
        self.assertEqual(srv.verify_task('task_1',True,verifier_agent_id='missing')['code'],404)

    def test_legacy_cannot_bypass_integrity(self):
        t=self.pending();t['result']=''
        r=srv.verify_task('task_1',True,approved_credits=100,verifier_agent_id='r')
        self.assertEqual(r['task']['status'],'open')
        self.assertEqual(srv.state['agents']['a']['credits'],0)

    def test_receipt_hash_covers_final_shares(self):
        self.pending()
        receipt=dict(srv.verify_task('task_1',True,verifier_agent_id='r')['verification_receipt'])
        sig=receipt.pop('signature')
        self.assertEqual(sig,'stub:'+hashlib.sha256((json.dumps(receipt,sort_keys=True)+srv.state['server_salt']).encode()).hexdigest()[:32])

    def test_negative_bounty_rejected(self):
        t,e=srv.create_task('goal_1',{'bounty':-1})
        self.assertIsNone(t);self.assertEqual(e['code'],400)

    def test_artifact_bounds_and_terminal_immutability(self):
        t=mk_task(status='claimed',agent_id='a')
        self.assertEqual(srv.publish_artifact('task_1','a','result','x','x'*20001,'text/plain')['code'],400)
        self.assertIn('artifact',srv.publish_artifact('task_1','a','result','x','x'*20000,'text/plain'))
        t['status']='done'
        self.assertEqual(srv.publish_artifact('task_1','a','result','x','ok','text/plain')['code'],409)

    def test_idempotency_snapshot_is_immutable(self):
        result={'nested':{'value':1}}
        srv.record_idempotency('k',result);result['nested']['value']=2
        self.assertEqual(srv.check_idempotency('k')['nested']['value'],1)

class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.Integration.setUpClass.__func__(cls)
        _,a=http('POST','/api/agents/register',{'name':'Audit'});cls.aid=a['id']
    @classmethod
    def tearDownClass(cls):
        baseline.Integration.tearDownClass.__func__(cls)
    def goal(self):
        return http('POST','/api/goals',{'title':'Audit','budget':100})[1]['id']
    def task(self,g,**kw):
        return http('POST',f'/api/goals/{g}/tasks',{'title':'Task',**kw})[1]['id']
    def test_dependency_blocks_claim(self):
        g=self.goal();a=self.task(g);b=self.task(g,dependencies=[a])
        self.assertEqual(http('POST',f'/api/tasks/{b}/claim',{'agent_id':self.aid})[0],409)
    def test_empty_clarification_rejected(self):
        t=self.task(self.goal(),effort=5)
        self.assertEqual(http('POST',f'/api/tasks/{t}/clarify',{})[0],400)
    def test_retry_scoped_to_task(self):
        g=self.goal();a=self.task(g);b=self.task(g)
        payload={'agent_id':self.aid,'idempotency_key':'shared'}
        ra=http('POST',f'/api/tasks/{a}/claim',payload)[1]
        rb=http('POST',f'/api/tasks/{b}/claim',payload)[1]
        self.assertEqual(ra['task']['id'],a);self.assertEqual(rb['task']['id'],b)
    def test_concurrent_retry_one_escrow(self):
        g=self.goal();t=self.task(g,bounty=7)
        with ThreadPoolExecutor(max_workers=4) as ex:
            results=list(ex.map(lambda _:http('POST',f'/api/tasks/{t}/claim',{'agent_id':self.aid,'idempotency_key':'retry'}),range(4)))
        self.assertTrue(all(code==200 for code,_ in results))
        s=http('GET','/api/state')[1]
        self.assertEqual(s['goals'][g]['budget_available'],93)
    def test_invalid_credits_no_mutation(self):
        for v in (-10,'5',True,float('inf'),.001):
            self.assertEqual(http('POST','/api/goals',{'budget':v})[0],400)
    def test_cross_origin_and_host_blocked(self):
        for headers in ({'Origin':'https://evil.example'},{'Host':'evil.example'}):
            req=urllib.request.Request('http://127.0.0.1:8479/api/goals',data=b'{}',headers={'Content-Type':'application/json',**headers})
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(req)
            self.assertEqual(caught.exception.code,403)
    def test_private_fields_omitted(self):
        s=http('GET','/api/state')[1]
        self.assertNotIn('server_salt',s);self.assertNotIn('idempotency',s)

if __name__=='__main__':unittest.main(verbosity=2)
