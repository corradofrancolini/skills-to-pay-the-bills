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

# Args: [--ttl MINUTES] [--no-isolate] [--auth] <path>
ttl=0
isolate_single=1
auth=0
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --ttl) ttl="${2:-0}"; shift 2 ;;
    --no-isolate) isolate_single=0; shift ;;
    --auth) auth=1; shift ;;
    --) shift; while [ $# -gt 0 ]; do args+=("$1"); shift; done ;;
    *) args+=("$1"); shift ;;
  esac
done
set -- "${args[@]:-}"

script_dir="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "Error: specify the path to expose. Usage: launch-tunnel.sh [--ttl MINUTES] [--no-isolate] <path>" >&2
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

state_dir="/tmp/temp-pub"
mkdir -p "$state_dir"
http_pid_file="$state_dir/.http.pid"
tunnel_pid_file="$state_dir/.tunnel.pid"
http_log="$state_dir/.http.log"
tunnel_log="$state_dir/.tunnel.log"
served_marker="$state_dir/.servedir"
rm -f "$served_marker"

# Resolve the directory to serve.
#  - folder: serve it directly.
#  - single file: ISOLATE by default (copy into a fresh dir) so sibling files are
#    never exposed, then append the filename to the public URL. --no-isolate serves
#    the parent directory instead.
filename_suffix=""
if [ -d "$target" ]; then
  abs_dir="$(cd "$target" && pwd)"
else
  src="$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"
  filename_suffix="/$(basename "$target")"
  if [ "$isolate_single" = "1" ]; then
    iso="$state_dir/share-$(date +%s)-$$"
    mkdir -p "$iso"
    cp "$src" "$iso/"
    abs_dir="$iso"
    echo "$iso" > "$served_marker"
  else
    abs_dir="$(dirname "$src")"
  fi
fi

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

# Start the local HTTP server (plain, or Basic-Auth-protected with --auth).
auth_user=""
auth_pass=""
if [ "$auth" = "1" ]; then
  auth_user="guest"
  auth_pass="$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')"
  # Password passed via env (not argv) so it never appears in `ps`.
  TEMPPUB_USER="$auth_user" TEMPPUB_PASS="$auth_pass" \
    nohup python3 "$script_dir/authserver.py" --port "$port" --bind 127.0.0.1 --dir "$abs_dir" > "$http_log" 2>&1 &
  echo "$auth_user" > "$state_dir/.auth"
else
  nohup python3 -m http.server "$port" --bind 127.0.0.1 --directory "$abs_dir" > "$http_log" 2>&1 &
fi
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

# Record state for `status-tunnel.sh`.
date +%s > "$state_dir/.start"
printf "%s" "$full_url" > "$state_dir/.url"

if [ "$auth" = "1" ]; then
  echo "(protected — user: ${auth_user}  password: ${auth_pass})" >&2
fi

# Optional auto-stop after --ttl minutes (avoids "forgotten open link").
# IMPORTANT: redirect the watcher's stdin/out/err to /dev/null so it does NOT keep
# the caller's stdout pipe open — otherwise `url=$(launch-tunnel.sh --ttl N ...)`
# would block until the sleep finishes.
if [ "${ttl:-0}" -gt 0 ] 2>/dev/null; then
  ttl_script_dir="$(cd "$(dirname "$0")" && pwd)"
  touch "$state_dir/.ttl.active"   # marker: removing it cancels the watcher
  (
    for ((k = 0; k < ttl; k++)); do
      sleep 60
      [ -f "$state_dir/.ttl.active" ] || exit 0   # cancelled by stop-tunnel.sh
    done
    rm -f "$state_dir/.ttl.pid"                    # so stop won't try to kill us mid-run
    bash "$ttl_script_dir/stop-tunnel.sh"
  ) >/dev/null 2>&1 </dev/null &
  echo $! > "$state_dir/.ttl.pid"
  disown 2>/dev/null || true
  echo "(auto-stop scheduled in ${ttl} min)" >&2
fi
