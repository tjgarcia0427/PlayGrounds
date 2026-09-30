"""Credential transport tests use synthetic secrets and a local HTTP server."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mcp_server as mcp

class Handler(BaseHTTPRequestHandler):
    requests = []
    echo = False
    def log_message(self, *args):
        pass
    def do_GET(self):
        self.requests.append((self.path, self.headers.get('Authorization')))
        if self.path.endswith('/redirect'):
            self.send_response(302); self.send_header('Location', '/captured'); self.end_headers()
        elif self.path.endswith('/error'):
            self.send_response(401); self.end_headers(); self.wfile.write(mcp.TOKEN.encode())
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps({'echo':mcp.TOKEN} if self.echo else {'ok':True}).encode())

class Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        self.old=(mcp.BASE,mcp.TOKEN,mcp.ROOM)
        mcp.BASE='http://127.0.0.1:'+str(self.server.server_port)
        mcp.TOKEN='synthetic-private-token';mcp.ROOM='room_test';Handler.requests.clear();Handler.echo=False
    def tearDown(self):
        mcp.BASE,mcp.TOKEN,mcp.ROOM=self.old
    def test_header_scope_and_identity(self):
        mcp.api('GET','/api/world');mcp.call_tool('playgrounds_identity',{})
        self.assertEqual(Handler.requests,[('/api/rooms/room_test/world','Bearer synthetic-private-token'),('/api/rooms/room_test','Bearer synthetic-private-token')])
        self.assertNotIn(mcp.TOKEN,str([p for p,_ in Handler.requests]))
        self.assertNotIn('playgrounds_register_agent',[t['name'] for t in mcp.available_tools()])
        with self.assertRaises(RuntimeError):mcp.call_tool('playgrounds_register_agent',{'name':'other'})
    def test_redirect_never_followed(self):
        with self.assertRaisesRegex(RuntimeError,'HTTP 302'):mcp.api('GET','/api/redirect')
        self.assertEqual(len(Handler.requests),1)
    def test_error_redacts_reflected_secret(self):
        with self.assertRaises(RuntimeError) as raised:mcp.api('GET','/api/error')
        self.assertNotIn(mcp.TOKEN,str(raised.exception))
    def test_success_response_cannot_echo_bearer(self):
        Handler.echo=True
        reply=mcp.handle({'id':1,'method':'tools/call','params':{'name':'playgrounds_world'}})
        self.assertNotIn(mcp.TOKEN,json.dumps(reply))
        self.assertIn('[redacted]',json.dumps(reply))
    def test_remote_tls_and_origin_validation(self):
        for base in ['http://example.invalid','https://u:secret@example.invalid','https://example.invalid/path','https://example.invalid?token=secret','https://example.invalid/#fragment']:
            mcp.BASE=base
            with self.assertRaises(RuntimeError):mcp.api('GET','/api/world')
        self.assertEqual(Handler.requests,[])
    def test_room_requires_key_and_safe_id(self):
        mcp.TOKEN=''
        with self.assertRaises(RuntimeError):mcp.api('GET','/api/world')
        mcp.TOKEN='synthetic';mcp.ROOM='room_x/../../lobby'
        with self.assertRaises(RuntimeError):mcp.api('GET','/api/world')
        with self.assertRaises(RuntimeError):mcp.call_tool('playgrounds_claim_task',{'task_id':'../room_other','agent_id':'a'})
    def test_legacy_local_lobby_preserved(self):
        mcp.ROOM='';mcp.TOKEN='';mcp.api('GET','/api/world')
        self.assertEqual(Handler.requests,[('/api/world',None)])
        self.assertEqual(mcp.available_tools(),mcp.TOOLS)

if __name__=='__main__':unittest.main(verbosity=2)
