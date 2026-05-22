#!/usr/bin/env bash
# Copy selected files/folders into an isolated /tmp/temp-pub/<timestamp>/ directory.
# Usage: safe-prepare-share.sh <source_path> [more_paths...]
# Prints the isolated directory path on stdout (last line).
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Error: provide at least one file or folder to prepare." >&2
  exit 1
fi

ts="$(date +%Y%m%d-%H%M%S)"
dest="/tmp/temp-pub/${ts}"
mkdir -p "$dest"

for src in "$@"; do
  if [ ! -e "$src" ]; then
    echo "Error: '$src' does not exist." >&2
    exit 1
  fi
  cp -R "$src" "$dest/"
done

echo "$dest"
