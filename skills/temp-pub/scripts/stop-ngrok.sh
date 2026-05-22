#!/usr/bin/env bash
# Stop the ngrok tunnel started by launch-ngrok.sh.
# Idempotent: safe to run when no tunnel is active.
set -u

pid_file="/tmp/temp-pub/.ngrok.pid"

if [ ! -f "$pid_file" ]; then
  echo "Nessun tunnel attivo."
  exit 0
fi

pid="$(cat "$pid_file" 2>/dev/null || true)"
rm -f "$pid_file"

if [ -z "$pid" ]; then
  echo "Nessun PID registrato."
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  kill "$pid" 2>/dev/null || true
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  echo "Tunnel chiuso."
else
  echo "Il processo non era più attivo."
fi
