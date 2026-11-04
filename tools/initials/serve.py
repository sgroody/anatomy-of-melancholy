"""A local server for rendering the edition's decorated initials with initialis (work/vendor/initialis).

Serves the repository root on 127.0.0.1 (so the render page can import the vendored library, cloned into
work/vendor/initialis at the commit in data/source/INITIALS.lock, and its workers from the same origin) and accepts
POST /save?name=<file>.png, writing the body to work/initials-render/out/ (git-ignored). Names are
restricted to letters, digits, dots, dashes and underscores; nothing is written anywhere else.
"""

import http.server
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "work" / "initials-render" / "out"
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}\.(png|webp|json)$")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript",
                      ".mjs": "text/javascript", ".json": "application/json", ".wasm": "application/wasm"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        name = (parse_qs(u.query).get("name") or [""])[0]
        if u.path != "/save" or not NAME.match(name):
            self.send_error(400, "bad save request")
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20_000_000:
            self.send_error(413)
            return
        OUT.mkdir(exist_ok=True)
        (OUT / name).write_bytes(self.rfile.read(n))
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"initials render server at http://127.0.0.1:{port}/tools/initials/render.html", flush=True)
        httpd.serve_forever()
