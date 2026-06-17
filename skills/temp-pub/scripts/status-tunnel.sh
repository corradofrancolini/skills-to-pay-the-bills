#!/usr/bin/env bash
# Show the status of the Cloudflare Quick Tunnel started by launch-tunnel.sh:
# whether it's active, the public URL, how long it's been up, how many requests
# it has served, and whether an auto-stop (--ttl) is scheduled.
set -u

state_dir="/tmp/temp-pub"
tunnel_pid_file="$state_dir/.tunnel.pid"

pid="$(cat "$tunnel_pid_file" 2>/dev/null || true)"
if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
  echo "No active tunnel."
  exit 0
fi

url="$(cat "$state_dir/.url" 2>/dev/null || echo '?')"
echo "Active. URL: $url"

start="$(cat "$state_dir/.start" 2>/dev/null || true)"
if [ -n "$start" ]; then
  now="$(date +%s)"
  mins=$(( (now - start) / 60 ))
  echo "Up for ~${mins} min"
fi

hits="$(grep -cE '"(GET|HEAD)' "$state_dir/.http.log" 2>/dev/null)"
echo "Requests served: ${hits:-0}"

ttl_pid="$(cat "$state_dir/.ttl.pid" 2>/dev/null || true)"
if [ -n "$ttl_pid" ] && kill -0 "$ttl_pid" 2>/dev/null; then
  echo "Auto-stop: scheduled."
else
  echo "Auto-stop: none (runs until you stop it)."
fi
