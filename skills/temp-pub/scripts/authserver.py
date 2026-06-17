#!/usr/bin/env python3
"""Tiny static file server with HTTP Basic Auth, used by launch-tunnel.sh when
--auth is requested. Credentials come from the environment (never argv, so they
don't show up in `ps`):
    TEMPPUB_USER (default "guest")  and  TEMPPUB_PASS (required)
Serves --dir on 127.0.0.1:--port. The Cloudflare tunnel in front is HTTPS, so
the Basic credentials are protected in transit.
"""
import argparse
import base64
import functools
import hmac
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

USER = os.environ.get("TEMPPUB_USER", "guest")
PASS = os.environ.get("TEMPPUB_PASS", "")


class AuthHandler(SimpleHTTPRequestHandler):
    def _authorized(self) -> bool:
        hdr = self.headers.get("Authorization", "")
        if not hdr.startswith("Basic "):
            return False
        try:
            user, _, pw = base64.b64decode(hdr[6:]).decode("utf-8", "ignore").partition(":")
        except Exception:
            return False
        return hmac.compare_digest(user, USER) and hmac.compare_digest(pw, PASS)

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="temp-pub"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Authentication required.\n")

    def do_GET(self):
        if not self._authorized():
            return self._deny()
        return super().do_GET()

    def do_HEAD(self):
        if not self._authorized():
            return self._deny()
        return super().do_HEAD()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--bind", default="127.0.0.1")
    args = ap.parse_args()
    if not PASS:
        print("authserver: TEMPPUB_PASS not set in environment", file=sys.stderr)
        sys.exit(1)
    handler = functools.partial(AuthHandler, directory=args.dir)
    HTTPServer((args.bind, args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
