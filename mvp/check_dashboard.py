"""Parse every inline dashboard script with Node; does not require a browser."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import tempfile

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.active = False
    def handle_starttag(self, tag, attrs):
        if tag == "script" and "src" not in dict(attrs):
            self.active = True
            self.scripts.append("")
    def handle_data(self, data):
        if self.active:
            self.scripts[-1] += data
    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False

parser = Scripts()
parser.feed(Path(__file__).with_name("dashboard.html").read_text())
assert parser.scripts, "No inline dashboard scripts found"
with tempfile.TemporaryDirectory(prefix="playgrounds-js-") as directory:
    for index, source in enumerate(parser.scripts):
        path = Path(directory) / f"dashboard-{index}.js"
        path.write_text(source)
        subprocess.run(["node", "--check", str(path)], check=True)
print(f"Dashboard syntax OK ({len(parser.scripts)} inline scripts); visual behavior not tested")
