#!/usr/bin/env bash
# Launch an ngrok tunnel serving a local file or folder, capture the public URL,
# save the PID, and copy the URL to the clipboard.
# Usage: launch-ngrok.sh <path>
# On success prints the public URL on stdout.
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

# ngrok's file:// backend requires a directory. For single files, serve the parent
# directory and append the filename to the public URL at the end.
filename_suffix=""
if [ -d "$target" ]; then
  abs_dir="$(cd "$target" && pwd)"
else
  abs_dir="$(cd "$(dirname "$target")" && pwd)"
  filename_suffix="/$(basename "$target")"
fi

state_dir="/tmp/temp-pub"
mkdir -p "$state_dir"
pid_file="$state_dir/.ngrok.pid"
log_file="$state_dir/.ngrok.log"

# Stop any previous tunnel started by this skill.
if [ -f "$pid_file" ]; then
  old_pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$pid_file"
fi

# Launch ngrok in background. `--log=stdout` makes the local API populate quickly.
nohup ngrok http "file://${abs_dir}" --log=stdout > "$log_file" 2>&1 &
echo $! > "$pid_file"

# Poll local API for the public URL (max ~15s).
url=""
for _ in $(seq 1 30); do
  sleep 0.5
  url="$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys, json
try:
  d = json.load(sys.stdin)
  ts = d.get('tunnels', [])
  if ts:
    print(ts[0].get('public_url',''))
except Exception:
  pass" 2>/dev/null || true)"
  if [ -n "$url" ]; then break; fi
done

if [ -z "$url" ]; then
  echo "Error: could not read the public URL from ngrok. Log: $log_file" >&2
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
