#!/usr/bin/env python3
"""c2c secret scanner.

Scans a project's tracked text files and/or a specific draft file for secret VALUES
that must never enter a handoff bundle. Pattern set is shared with
file-curator/scripts/detect_sensitive.py (CONTENT_PATTERNS) plus .env assignments.

Emits JSON: {"result": "clean"|"flagged", "findings": [...]}. Values are redacted in
the output so the report itself never leaks a secret.

Usage:
    python3 scan_secrets.py <project-path>            # scan tracked/text files
    python3 scan_secrets.py <project-path> --text F   # also scan draft file F
    python3 scan_secrets.py --text F                  # scan only F
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Shared with file-curator detect_sensitive.py, extended for handoff drafts.
CONTENT_PATTERNS = [
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "IBAN"),
    (re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T][\dLMNP-V]{2}[A-Z]\d{3}[A-Z]\b"), "Italian Codice Fiscale"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\b(api[_-]?key|secret[_-]?key|access[_-]?token)\b[\"'\s:=]+[A-Za-z0-9/_+-]{16,}", re.I), "API key/token in content"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI-style secret key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "GitHub PAT"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"(?m)^\s*(export\s+)?[A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*\s*=\s*[\"']?[^\s\"']{8,}"), "env-style secret assignment"),
]

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             ".next", ".handoff"}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml",
                 ".yml", ".toml", ".ini", ".cfg", ".env", ".sh", ".rb", ".go", ".rs",
                 ".java", ".php", ".html", ".css", ".sql", ".xml", ""}
MAX_BYTES = 512_000


def redact(value: str) -> str:
    v = value.strip()
    if len(v) <= 8:
        return "***"
    return f"{v[:3]}…{v[-2:]} ({len(v)} chars)"


def scan_text(text: str, source: str) -> list[dict]:
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat, label in CONTENT_PATTERNS:
            m = pat.search(line)
            if m:
                findings.append({"source": source, "line": i, "type": label,
                                 "redacted": redact(m.group(0))})
    return findings


def tracked_files(project: Path) -> list[Path]:
    try:
        out = subprocess.run(["git", "-C", str(project), "ls-files"],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            return [project / p for p in out.stdout.strip().split("\n")]
    except Exception:
        pass
    # fallback: walk
    files = []
    for p in project.rglob("*"):
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts):
            files.append(p)
    return files


def scan_file(path: Path) -> list[dict]:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return []
    try:
        if path.stat().st_size > MAX_BYTES:
            return []
        text = path.read_text(errors="replace")
    except Exception:
        return []
    return scan_text(text, str(path))


def main(argv: list[str]) -> int:
    project = None
    text_file = None
    i = 0
    while i < len(argv):
        if argv[i] == "--text":
            text_file = Path(argv[i + 1]).expanduser()
            i += 2
        else:
            project = Path(argv[i]).expanduser().resolve()
            i += 1

    findings: list[dict] = []
    if project:
        if not project.is_dir():
            print(json.dumps({"error": f"not a directory: {project}"}))
            return 2
        for f in tracked_files(project):
            findings.extend(scan_file(f))
    if text_file:
        if not text_file.is_file():
            print(json.dumps({"error": f"not a file: {text_file}"}))
            return 2
        findings.extend(scan_text(text_file.read_text(errors="replace"), str(text_file)))

    result = {
        "result": "flagged" if findings else "clean",
        "scanned_project": str(project) if project else None,
        "scanned_text": str(text_file) if text_file else None,
        "count": len(findings),
        "findings": findings,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
