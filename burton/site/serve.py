"""`burton serve`: a local static server for the built site (127.0.0.1 only)."""

import functools
import http.server

from .. import paths


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".woff2": "font/woff2",
                      ".js": "text/javascript", ".svg": "image/svg+xml"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = False  # on Windows it would let a second server take a port that is in use


def serve(profile: str, port: int, open_browser: bool = False) -> None:
    root = paths.SITE / profile
    if not (root / "index.html").exists():
        raise SystemExit(f"site/{profile} is not built: run `burton build --profile {profile}`")
    handler = functools.partial(Handler, directory=str(root))
    for p in range(port, port + 10):  # a busy port (another server) moves to the next free one
        try:
            httpd = Server(("127.0.0.1", p), handler)
            break
        except OSError:
            print(f"port {p} is in use; trying {p + 1}")
    else:
        raise SystemExit(f"no free port in {port}-{port + 9}")
    if p != port:
        print("(reading options and the offline copy belong to each port, so they start afresh on this one)")
    port = p
    with httpd:
        print(f"serving site/{profile} at http://127.0.0.1:{port}/  (Ctrl+C to stop)", flush=True)
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://127.0.0.1:{port}/")
        httpd.serve_forever()
