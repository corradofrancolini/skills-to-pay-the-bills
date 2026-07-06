#!/usr/bin/env python3
"""c2c sender-side miner.

Gather the machine-readable signals that PRE-FILL the exit interview. Emits a JSON
report to stdout. Never fails hard on a missing piece — reports what it found and
what it couldn't, so the interview can target the gaps.

Usage:
    python3 mine_project.py <project-path>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEP_MANIFESTS = [
    "package.json", "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock",
    "go.mod", "Cargo.toml", "Gemfile", "pom.xml", "build.gradle", "composer.json",
]
STATE_GLOBS = ["SESSION_HANDOFF.md", "docs/SESSION_HANDOFF.md", "STATE.md", ".gsd/STATE.md"]


def git(project: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def memory_dir_candidates(project: Path) -> list[dict]:
    """The remember plugin keys memory by slugified absolute path, OUTSIDE the repo."""
    base = Path.home() / ".claude" / "projects"
    abs_str = str(project)
    cands = {
        abs_str.replace("/", "-"),
        "".join(c if c.isalnum() else "-" for c in abs_str),
    }
    found = []
    for slug in cands:
        d = base / slug / "memory"
        if d.exists():
            notes = sorted(p.name for p in d.glob("*.md"))
            found.append({"path": str(d), "has_index": (d / "MEMORY.md").exists(),
                          "notes": notes})
    return found


def main(argv: list[str]) -> int:
    if not argv:
        print(json.dumps({"error": "usage: mine_project.py <project-path>"}))
        return 2
    project = Path(argv[0]).expanduser().resolve()
    if not project.is_dir():
        print(json.dumps({"error": f"not a directory: {project}"}))
        return 2

    report: dict = {"project_path": str(project), "project_name": project.name}

    # --- git ---
    is_git = (project / ".git").exists() or git(project, "rev-parse", "--git-dir") is not None
    report["git"] = {"is_repo": bool(is_git)}
    if is_git:
        report["git"]["head_commit"] = git(project, "rev-parse", "HEAD")
        report["git"]["branch"] = git(project, "rev-parse", "--abbrev-ref", "HEAD")
        report["git"]["branches"] = (git(project, "branch", "--format=%(refname:short)") or "").split("\n")
        report["git"]["commit_count"] = git(project, "rev-list", "--count", "HEAD")
        report["git"]["recent"] = (git(project, "log", "-15", "--pretty=%h %ad %s", "--date=short") or "").split("\n")
        # most-churned files = architectural center of gravity
        churn = git(project, "log", "--name-only", "--pretty=format:", "-200")
        if churn:
            counts: dict[str, int] = {}
            for line in churn.split("\n"):
                line = line.strip()
                if line:
                    counts[line] = counts.get(line, 0) + 1
            top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:15]
            report["git"]["top_churned"] = [{"file": f, "touches": n} for f, n in top]
        report["git"]["uncommitted"] = bool(git(project, "status", "--porcelain"))

    # --- config & knowledge sources ---
    report["project_claude_md"] = (project / "CLAUDE.md").exists()
    report["state_files"] = [g for g in STATE_GLOBS if (project / g).exists()]
    report["mcp_json"] = None
    mcp = project / ".mcp.json"
    if mcp.exists():
        try:
            data = json.loads(mcp.read_text())
            servers = list(data.get("mcpServers", {}).keys())
            # surface absolute paths that would break on another machine
            abs_paths = []
            for name, cfg in data.get("mcpServers", {}).items():
                for k in ("cwd",):
                    v = cfg.get(k)
                    if isinstance(v, str) and v.startswith("/"):
                        abs_paths.append({"server": name, "key": k, "value": v})
                for k, v in (cfg.get("env") or {}).items():
                    if isinstance(v, str) and v.startswith("/"):
                        abs_paths.append({"server": name, "key": f"env.{k}", "value": v})
            report["mcp_json"] = {"servers": servers, "absolute_paths": abs_paths}
        except Exception as e:
            report["mcp_json"] = {"error": f"unparseable: {e}"}

    report["dependency_manifests"] = [m for m in DEP_MANIFESTS if (project / m).exists()]
    report["has_backlog"] = (project / "backlog").is_dir()
    report["has_plans"] = (project / "plans").is_dir() or (project / ".claude" / "plans").is_dir()
    report["ships_claude_dir"] = (project / ".claude").is_dir()
    if report["ships_claude_dir"]:
        cdir = project / ".claude"
        report["claude_dir_contents"] = sorted(p.name for p in cdir.iterdir())

    # --- the silent-dependency trap: out-of-tree memory ---
    report["memory_dirs"] = memory_dir_candidates(project)

    # --- gentle nudges for the interview ---
    gaps = []
    if not report["project_claude_md"]:
        gaps.append("No project CLAUDE.md — ask the owner for the project's purpose & conventions.")
    if not report["state_files"]:
        gaps.append("No SESSION_HANDOFF/state file — ask for current state (works/in-progress/blocked).")
    if report["memory_dirs"]:
        gaps.append("Out-of-tree memory exists — distill it into the bundle; it will NOT travel with git.")
    if report.get("mcp_json") and report["mcp_json"].get("absolute_paths"):
        gaps.append("Project .mcp.json has absolute paths — flag for path audit in environment.md.")
    report["interview_gaps"] = gaps

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
