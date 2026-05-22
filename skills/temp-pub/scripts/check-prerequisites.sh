#!/usr/bin/env bash
# Detect prerequisites for the temp-pub skill.
# Output: single-line JSON on stdout — {"platform","brew","ngrok","authtoken"}.
# Exit code is always 0 unless the script itself is broken; consumers parse JSON.
set -u

platform="$(uname -s | tr '[:upper:]' '[:lower:]')"

has_cmd() { command -v "$1" >/dev/null 2>&1; }

brew_ok=false
if [ "$platform" = "darwin" ] && has_cmd brew; then
  brew_ok=true
fi

ngrok_ok=false
if has_cmd ngrok; then
  ngrok_ok=true
fi

# `ngrok config check` exits 0 only when an authtoken is configured.
authtoken_ok=false
if $ngrok_ok; then
  if ngrok config check >/dev/null 2>&1; then
    authtoken_ok=true
  fi
fi

printf '{"platform":"%s","brew":%s,"ngrok":%s,"authtoken":%s}\n' \
  "$platform" "$brew_ok" "$ngrok_ok" "$authtoken_ok"
