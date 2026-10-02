"""Real backend regression for the Host/Origin contract used by Caddy."""
import http.client
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest


class HostingContract(unittest.TestCase):
    def test_public_host_and_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = dict(os.environ, PLAYGROUNDS_PORT=str(port),
                       PLAYGROUNDS_STATE_PATH=tmp + '/state.json',
                       PLAYGROUNDS_ALLOWED_HOSTS='pilot.example.test',
                       PLAYGROUNDS_OPERATOR_TOKEN='synthetic-host-test',
                       PLAYGROUNDS_TRUSTED_ORIGIN='')
            server = Path(__file__).resolve().parents[1] / 'mvp/server.py'
            proc = subprocess.Popen([sys.executable, str(server)], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            def request(method, path, host, origin=None, authenticated=False):
                headers = {'Host': host, 'Content-Type': 'application/json'}
                if origin:
                    headers['Origin'] = origin
                if authenticated:
                    headers['Authorization'] = 'Bearer synthetic-host-test'
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
                try:
                    conn.request(method, path, '{}' if method == 'POST' else None, headers)
                    response = conn.getresponse()
                    response.read()
                    return response.status
                finally:
                    conn.close()
            try:
                for attempt in range(100):
                    try:
                        status = request('GET', '/', 'pilot.example.test')
                        break
                    except OSError:
                        time.sleep(.05)
                else:
                    self.fail('backend did not start')
                self.assertEqual(status, 200)
                self.assertEqual(request('GET', '/', 'evil.example.test'), 403)
                self.assertEqual(request('GET', '/api/state', 'pilot.example.test'), 403)
                self.assertEqual(request('GET', '/api/state', 'pilot.example.test', authenticated=True), 200)
                # Unknown routes return 404 only after Host and Origin checks pass.
                self.assertEqual(request('POST', '/not-a-route', 'pilot.example.test', 'https://pilot.example.test', True), 404)
                self.assertEqual(request('POST', '/not-a-route', 'pilot.example.test', 'https://evil.example.test', True), 403)
            finally:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
