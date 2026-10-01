"""Native current-checkout backend and static routing; fresh QA state only."""
import os
from pathlib import Path
import sys
import tempfile

state = Path(os.environ['PLAYGROUNDS_STATE_PATH']).resolve()
if not state.is_relative_to(Path(tempfile.gettempdir()).resolve()) or state.exists():
    raise RuntimeError('Requires fresh temporary state')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as app

app.ThreadingHTTPServer(('127.0.0.1', app.PORT), app.Handler).serve_forever()
