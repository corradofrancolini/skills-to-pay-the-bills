#!/usr/bin/env bash
# Copy selected files/folders into an isolated /tmp/temp-pub/<timestamp>/ directory.
# Usage: safe-prepare-share.sh <source_path> [more_paths...]
# Prints the isolated directory path on stdout (last line).
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Errore: indica almeno un file o cartella da preparare." >&2
  exit 1
fi

ts="$(date +%Y%m%d-%H%M%S)"
dest="/tmp/temp-pub/${ts}"
mkdir -p "$dest"

for src in "$@"; do
  if [ ! -e "$src" ]; then
    echo "Errore: '$src' non esiste." >&2
    exit 1
  fi
  cp -R "$src" "$dest/"
done

echo "$dest"
