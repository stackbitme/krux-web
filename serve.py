#!/usr/bin/env python3
"""Local server for the Krux web simulator.

    python3 serve.py            # http://localhost:8000
    python3 serve.py 9000       # another port

Serves the `web/` folder with the two headers browsers require for shared
memory (Cross-Origin-Opener-Policy / Cross-Origin-Embedder-Policy). Only
needs Python 3 (no packages). Works offline.
"""
import http.server
import os
import socketserver
import sys
import threading
import webbrowser

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".wasm": "application/wasm",
        ".json": "application/json",
        ".zip": "application/zip",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".kfnt": "application/octet-stream",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    for p in range(port, port + 20):
        try:
            httpd = Server(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit("No free port between %d and %d" % (port, port + 19))
    url = "http://localhost:%d/" % httpd.server_address[1]
    print("Simulador Krux em %s  (Ctrl+C para encerrar)" % url)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
