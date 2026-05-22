#!/usr/bin/env bash
# Launch a Cloudflare Quick Tunnel serving a local file or folder.
# Usage: launch-tunnel.sh <path>
# On success prints the public URL on stdout and copies it to clipboard.
#
# How it works: cloudflared's Quick Tunnel needs an HTTP backend, not file://,
# so we start a small Python http.server on a free local port pointed at the
# target directory, then expose that port via `cloudflared tunnel --url`.
# Two PIDs are tracked (http server + cloudflared) for clean shutdown.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Error: specify the path to expose." >&2
  exit 1
fi

target="$1"
if [ ! -e "$target" ]; then
  echo "Error: '$target' does not exist." >&2
  exit 1
fi

# Defense-in-depth: refuse to expose home, root, or system directories.
if [ -d "$target" ]; then
  abs_check="$(cd "$target" && pwd)"
else
  abs_check="$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"
fi
case "$abs_check" in
  "$HOME"|"$HOME"/|/|/etc|/etc/*|/var|/var/*|/usr|/usr/*|/System|/System/*|/Library|/Library/*|/private|/private/*|/bin|/bin/*|/sbin|/sbin/*|/dev|/dev/*)
    echo "Error: path '$abs_check' is too broad or a system directory. Pick a more specific path." >&2
    exit 1
    ;;
esac

# Resolve the directory to serve. For a single file, serve its parent and append
# the filename to the public URL at the end.
filename_suffix=""
if [ -d "$target" ]; then
  abs_dir="$(cd "$target" && pwd)"
else
  abs_dir="$(cd "$(dirname "$target")" && pwd)"
  filename_suffix="/$(basename "$target")"
fi

state_dir="/tmp/temp-pub"
mkdir -p "$state_dir"
http_pid_file="$state_dir/.http.pid"
tunnel_pid_file="$state_dir/.tunnel.pid"
http_log="$state_dir/.http.log"
tunnel_log="$state_dir/.tunnel.log"

# Stop any previous tunnel/server started by this skill.
for pf in "$tunnel_pid_file" "$http_pid_file"; do
  if [ -f "$pf" ]; then
    old_pid="$(cat "$pf" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
      kill "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pf"
  fi
done
sleep 1

# Pick a free local port for the HTTP server.
port="$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()")"

# Start the local HTTP server.
nohup python3 -m http.server "$port" --bind 127.0.0.1 --directory "$abs_dir" > "$http_log" 2>&1 &
echo $! > "$http_pid_file"

# Give the server a moment to bind before cloudflared tries to reach it.
sleep 1

# Start the cloudflared quick tunnel.
nohup cloudflared tunnel --url "http://127.0.0.1:$port" > "$tunnel_log" 2>&1 &
echo $! > "$tunnel_pid_file"

# Poll the cloudflared log for the public URL (max ~30s).
url=""
for _ in $(seq 1 60); do
  sleep 0.5
  url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$tunnel_log" 2>/dev/null | head -1 || true)"
  if [ -n "$url" ]; then break; fi
done

if [ -z "$url" ]; then
  echo "Error: could not read the public URL from cloudflared. Log: $tunnel_log" >&2
  exit 1
fi

full_url="${url}${filename_suffix}"

# Copy to clipboard (best-effort, never fatal).
if command -v pbcopy >/dev/null 2>&1; then
  printf "%s" "$full_url" | pbcopy || true
elif command -v xclip >/dev/null 2>&1; then
  printf "%s" "$full_url" | xclip -selection clipboard || true
elif command -v wl-copy >/dev/null 2>&1; then
  printf "%s" "$full_url" | wl-copy || true
fi

echo "$full_url"
