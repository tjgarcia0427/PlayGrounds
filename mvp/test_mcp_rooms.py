"""Real pinned room backend + real stdio MCP processes; synthetic credentials only.

Compatibility test, NOT approval of PR23's pending SSE repair or public deployment.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import unittest

BACKEND = os.environ.get('ROOM_BACKEND_ROOT')
MCP = Path(__file__).with_name('mcp_server.py').resolve()

@unittest.skipUnless(BACKEND, 'ROOM_BACKEND_ROOT must point to pinned secure-room checkout')
class Rooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='pg-mcp-room-')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        cls.base=f'http://127.0.0.1:{port}';cls.operator=secrets.token_urlsafe(32)
        env={**os.environ,'PLAYGROUNDS_PORT':str(port),'PLAYGROUNDS_STATE_PATH':str(Path(cls.temp.name)/'state.json'),'PLAYGROUNDS_OPERATOR_TOKEN':cls.operator}
        cls.process=subprocess.Popen([sys.executable,str(Path(BACKEND)/'mvp/server.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for _ in range(100):
            try:cls.http('/api/policy',token=cls.operator);break
            except Exception:time.sleep(.05)
        else:raise RuntimeError('Room test backend failed to start')
    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();out,err=cls.process.communicate(timeout=10)
        for secret in getattr(cls,'credentials',[cls.operator]):
            assert secret.encode() not in out+err,'credential leaked in backend output'
        cls.temp.cleanup()
    @classmethod
    def http(cls,path,body=None,token=''):
        req=urllib.request.Request(cls.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
        with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
    def mcp(self,room,token,name,args=None,error=None):
        payload={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args or {}}}
        env={**os.environ,'PLAYGROUNDS_BASE':self.base,'PLAYGROUNDS_ROOM_ID':room,'PLAYGROUNDS_TOKEN':token}
        result=subprocess.run([sys.executable,str(MCP)],input=json.dumps(payload)+'\n',capture_output=True,text=True,env=env,timeout=30,check=True)
        if token:self.assertNotIn(token,result.stdout+result.stderr)
        response=json.loads(result.stdout)['result'];text=response['content'][0]['text']
        if error:
            self.assertTrue(response.get('isError'));self.assertIn(error,text);return
        self.assertFalse(response.get('isError'),text);return json.loads(text)
    def test_complete_authenticated_agent_loop_and_denials(self):
        created=self.http('/api/rooms',{'name':'MCP owner (QA)','space':'playground'},self.operator)
        rid=created['room']['id'];owner=created['token'];owner_id=created['agent']['id']
        invitation=self.http(f'/api/rooms/{rid}/invites',{},owner)
        joined=self.http(f'/api/rooms/{rid}/join',{'invite_token':invitation['token'],'name':'MCP worker (QA)','space':'playground'})
        member=joined['token'];aid=joined['agent']['id'];self.__class__.credentials=[self.operator,owner,member,invitation['token']]
        self.assertEqual(self.mcp(rid,member,'playgrounds_identity')['caller_agent_id'],aid)
        self.assertTrue(self.mcp(rid,member,'playgrounds_world')['authenticated'])
        self.mcp(rid,member,'playgrounds_heartbeat',{'agent_id':owner_id,'status':'idle'},error='403')
        self.mcp(rid,member,'playgrounds_register_agent',{'name':'imposter'},error='invitation')
        goal=self.mcp(rid,owner,'playgrounds_create_goal',{'title':'MCP room goal (QA)'})
        task=self.mcp(rid,owner,'playgrounds_create_task',{'goal_id':goal['id'],'title':'Real connector task (QA)','bounty':10})
        self.mcp(rid,member,'playgrounds_claim_task',{'task_id':task['id'],'agent_id':aid})
        self.mcp(rid,member,'playgrounds_progress',{'task_id':task['id'],'agent_id':aid,'note':'Authenticated checkpoint','progress_pct':.5})
        self.mcp(rid,member,'playgrounds_complete_task',{'task_id':task['id'],'agent_id':aid,'result':'Connector proof'})
        self.mcp(rid,member,'playgrounds_verify_task',{'task_id':task['id'],'verifier_agent_id':aid,'approved':True},error='403')
        result=self.mcp(rid,owner,'playgrounds_verify_task',{'task_id':task['id'],'verifier_agent_id':owner_id,'approved':True})
        self.assertEqual(result['task']['status'],'done');self.assertEqual(result['settlement_receipt']['payouts'][aid],9)
        other=self.http('/api/rooms',{'name':'Other room (QA)'},self.operator)
        self.mcp(other['room']['id'],member,'playgrounds_world',error='401')
        self.mcp(rid,'wrong-synthetic-key','playgrounds_world',error='401')
        self.mcp(rid,'','playgrounds_world',error='requires')
        self.http(f'/api/rooms/{rid}/members/{aid}/remove',{},owner)
        self.mcp(rid,member,'playgrounds_world',error='401')

if __name__=='__main__':unittest.main(verbosity=2)
