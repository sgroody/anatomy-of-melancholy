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


def serve(profile: str, port: int, open_browser: bool = False) -> None:
    root = paths.SITE / profile
    if not (root / "index.html").exists():
        raise SystemExit(f"site/{profile} is not built: run `burton build --profile {profile}`")
    handler = functools.partial(Handler, directory=str(root))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serving site/{profile} at http://127.0.0.1:{port}/  (Ctrl+C to stop)")
        if open_browser:
            import webbrowser

            webbrowser.open(f"http://127.0.0.1:{port}/")
        httpd.serve_forever()
