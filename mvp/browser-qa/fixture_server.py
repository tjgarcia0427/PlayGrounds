"""Isolated visual fixture: real protocol, deliberately long task deadlines.

Long software-rendered interaction tours must not trigger unrelated stall/lease
maintenance. Production defaults and stall regression suites are unchanged.
"""
import os
from pathlib import Path
import sys
import tempfile

state_path = Path(os.environ.get('PLAYGROUNDS_STATE_PATH', '')).resolve()
if not state_path.is_relative_to(Path(tempfile.gettempdir()).resolve()):
    raise RuntimeError('Visual fixture requires temporary state, never live state')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as app

app.STALL_AFTER = 3600
app.CLAIM_WINDOW = 3600
httpd = app.ThreadingHTTPServer(('127.0.0.1', app.PORT), app.Handler)
print('Isolated visual fixture: one-hour task deadlines; production defaults unchanged', flush=True)
httpd.serve_forever()
