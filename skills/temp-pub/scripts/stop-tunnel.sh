#!/usr/bin/env bash
# Stop the Cloudflare Quick Tunnel and the local HTTP server started by
# launch-tunnel.sh. Idempotent: safe to run when nothing is active.
set -u

state_dir="/tmp/temp-pub"
killed_any=false

# Cancel any pending auto-stop watcher (it self-exits within ~60s when the marker
# is gone), in addition to killing its recorded pid below.
rm -f "$state_dir/.ttl.active"

for label in ttl tunnel http; do
  pid_file="$state_dir/.${label}.pid"
  [ -f "$pid_file" ] || continue
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  rm -f "$pid_file"
  [ -z "$pid" ] && continue
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    killed_any=true
  fi
done

# Remove the isolated single-file share dir (if any) and the state files.
if [ -f "$state_dir/.servedir" ]; then
  served="$(cat "$state_dir/.servedir" 2>/dev/null || true)"
  case "$served" in "$state_dir"/share-*) [ -n "$served" ] && rm -rf "$served" ;; esac
  rm -f "$state_dir/.servedir"
fi
rm -f "$state_dir/.start" "$state_dir/.url"

if $killed_any; then
  echo "Tunnel stopped."
else
  echo "No active tunnel."
fi
