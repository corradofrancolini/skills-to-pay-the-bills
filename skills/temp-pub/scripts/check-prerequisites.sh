#!/usr/bin/env bash
# Detect prerequisites for the temp-pub skill.
# Output: single-line JSON on stdout — {"platform","brew","cloudflared","python3"}.
# Exit code is always 0 unless the script itself is broken; consumers parse JSON.
set -u

platform="$(uname -s | tr '[:upper:]' '[:lower:]')"

has_cmd() { command -v "$1" >/dev/null 2>&1; }

brew_ok=false
if [ "$platform" = "darwin" ] && has_cmd brew; then
  brew_ok=true
fi

cloudflared_ok=false
if has_cmd cloudflared; then
  cloudflared_ok=true
fi

# Python 3 is needed for the local HTTP server that backs the tunnel.
python3_ok=false
if has_cmd python3; then
  python3_ok=true
fi

printf '{"platform":"%s","brew":%s,"cloudflared":%s,"python3":%s}\n' \
  "$platform" "$brew_ok" "$cloudflared_ok" "$python3_ok"
