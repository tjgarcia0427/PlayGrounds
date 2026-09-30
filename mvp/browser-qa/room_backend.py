"""Real room backend + current UI static files, isolated integration only.

The dependency is checked out at an exact revision by CI. No API mocks or
security patches: only the two not-yet-merged UI script routes are added.
This is compatibility evidence, NOT approval of the backend or deployment.
"""
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlparse

state = Path(os.environ['PLAYGROUNDS_STATE_PATH']).resolve()
if not state.is_relative_to(Path(tempfile.gettempdir()).resolve()) or state.exists():
    raise RuntimeError('Requires fresh temporary state')
backend = Path(os.environ['ROOM_BACKEND_ROOT']).resolve() / 'mvp'
ui = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))
import server as app
app.ROOT = str(ui)
app.DASHBOARD_PATH = str(ui / 'dashboard.html')
app.AVATAR_DIR = str(ui / 'avatars')

class UIHandler(app.Handler):
    def _dispatch_get(self, parts, parsed):
        if parsed.path in ('/assets/room-ui.js', '/assets/invites.js', '/assets/ui.css'):
            path = ui / parsed.path.lstrip('/')
            if path.is_file():
                return self._send(200, path.read_bytes(), ('text/css' if path.suffix == '.css' else 'text/javascript') + '; charset=utf-8')
        return super()._dispatch_get(parts, parsed)

app.ThreadingHTTPServer(('127.0.0.1', app.PORT), UIHandler).serve_forever()
