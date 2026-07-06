#!/usr/bin/env python3
"""c2c bundle assembler (sender side).

Takes a spec JSON (assembled by Claude from the exit interview + mining) and writes the
handoff bundle into the repo: HANDOFF.md at root + .handoff/ with the knowledge pack and
manifest.yaml. Emits a JSON summary of what it wrote.

The spec carries all human-authored content; this script is pure I/O + manifest
serialization (no clock access — `created`/`source_commit` are passed in).

Usage:
    python3 assemble_bundle.py <project-path> --spec <spec.json>

Spec shape (see references/bundle-format.md):
{
  "created": "2026-07-06", "source_commit": "<sha>", "source_branch": "main",
  "project_name": "...",
  "sender": {"name": "...", "contact": "..."},
  "recipient_hint": "...", "first_task": "..." | null,
  "provenance_summary": {"declared": 0, "inferred": 0, "uncertain": 0},
  "sanitization": {"secret_scan": "clean", "scanned_at_commit": "<sha>",
                   "depersonalized": true, "paths_placeholdered": true},
  "environment": {"requires_mcp": [], "requires_secrets": [], "external_services": []},
  "status": "packaged",
  "handoff": {"summary": "...", "current_state": "...", "first_step": "..."},
  "files": {"project-brief.md": "...", "state-of-play.md": "...", ...}
}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KNOWLEDGE_FILES = [
    "project-brief.md", "state-of-play.md", "decision-log.md", "gotchas.md",
    "environment.md", "onboarding-protocol.md", "known-unknowns.md",
]
SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"


def yaml_scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or any(c in s for c in ':#\n"') or s != s.strip():
        return json.dumps(s, ensure_ascii=False)  # valid YAML double-quoted scalar
    return s


def yaml_list(items) -> str:
    if not items:
        return " []"
    return "\n" + "\n".join(f"    - {yaml_scalar(x)}" for x in items)


def build_manifest(spec: dict) -> str:
    s = spec
    sender = s.get("sender", {})
    prov = s.get("provenance_summary", {})
    san = s.get("sanitization", {})
    env = s.get("environment", {})
    lines = [
        "c2c_schema: 1",
        f"created: {yaml_scalar(s.get('created'))}",
        f"source_commit: {yaml_scalar(s.get('source_commit'))}",
        f"source_branch: {yaml_scalar(s.get('source_branch'))}",
        f"project_name: {yaml_scalar(s.get('project_name'))}",
        "sender:",
        f"  name: {yaml_scalar(sender.get('name'))}",
        f"  contact: {yaml_scalar(sender.get('contact'))}",
        f"recipient_hint: {yaml_scalar(s.get('recipient_hint'))}",
        f"first_task: {yaml_scalar(s.get('first_task'))}",
        "provenance_summary:",
        f"  declared: {yaml_scalar(prov.get('declared', 0))}",
        f"  inferred: {yaml_scalar(prov.get('inferred', 0))}",
        f"  uncertain: {yaml_scalar(prov.get('uncertain', 0))}",
        "sanitization:",
        f"  secret_scan: {yaml_scalar(san.get('secret_scan'))}",
        f"  scanned_at_commit: {yaml_scalar(san.get('scanned_at_commit'))}",
        f"  depersonalized: {yaml_scalar(san.get('depersonalized', False))}",
        f"  paths_placeholdered: {yaml_scalar(san.get('paths_placeholdered', False))}",
        "environment:",
        f"  requires_mcp:{yaml_list(env.get('requires_mcp', []))}",
        f"  requires_secrets:{yaml_list(env.get('requires_secrets', []))}",
        f"  external_services:{yaml_list(env.get('external_services', []))}",
        f"status: {yaml_scalar(s.get('status', 'packaged'))}",
    ]
    return "\n".join(lines) + "\n"


def build_handoff_md(spec: dict) -> str:
    tmpl_path = ASSETS / "HANDOFF.md.tmpl"
    tmpl = tmpl_path.read_text()
    h = spec.get("handoff", {})
    sender = spec.get("sender", {})
    repl = {
        "{{PROJECT_NAME}}": str(spec.get("project_name", "")),
        "{{SENDER_NAME}}": str(sender.get("name", "")),
        "{{CONTACT}}": str(sender.get("contact", "")),
        "{{CREATED}}": str(spec.get("created", "")),
        "{{SOURCE_COMMIT}}": str(spec.get("source_commit", "")),
        "{{SUMMARY}}": str(h.get("summary", "")),
        "{{CURRENT_STATE}}": str(h.get("current_state", "")),
        "{{FIRST_STEP}}": str(h.get("first_step", "")),
    }
    for k, v in repl.items():
        tmpl = tmpl.replace(k, v)
    return tmpl


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--spec":
        print(json.dumps({"error": "usage: assemble_bundle.py <project-path> --spec <spec.json>"}))
        return 2
    project = Path(argv[0]).expanduser().resolve()
    spec_path = Path(argv[2]).expanduser()
    if not project.is_dir():
        print(json.dumps({"error": f"not a directory: {project}"}))
        return 2
    if not spec_path.is_file():
        print(json.dumps({"error": f"spec not found: {spec_path}"}))
        return 2

    spec = json.loads(spec_path.read_text())
    handoff_dir = project / ".handoff"
    handoff_dir.mkdir(exist_ok=True)

    written = []
    files = spec.get("files", {})
    for name in KNOWLEDGE_FILES:
        content = files.get(name)
        if content is None:
            content = f"# {name}\n\n_(not provided)_\n"
        (handoff_dir / name).write_text(content)
        written.append(f".handoff/{name}")

    (handoff_dir / "manifest.yaml").write_text(build_manifest(spec))
    written.append(".handoff/manifest.yaml")

    (project / "HANDOFF.md").write_text(build_handoff_md(spec))
    written.append("HANDOFF.md")

    missing = [n for n in KNOWLEDGE_FILES if n not in files]
    print(json.dumps({
        "ok": True,
        "project": str(project),
        "written": written,
        "missing_knowledge_files": missing,
        "note": "Review HANDOFF.md + .handoff/ with the human before committing.",
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
