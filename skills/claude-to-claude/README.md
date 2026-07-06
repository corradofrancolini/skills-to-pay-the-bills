# claude-to-claude — Project Handoff Skill

Hand off **ownership** of a Claude Code project to another person who also uses Claude
Code — seamlessly. This is not a settings copy and not an account migration. It is an
**ownership transfer of code + understanding**, where the recipient's Claude arrives
already briefed and actively *onboards* the new human through the transition.

> **One-line mental model:** `git clone` moves the *visible* project. This skill moves the
> *invisible* one — why decisions were made, what's half-done, what's fragile, what must be
> reconstructed on the new machine, and what must never travel at all.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [The two modes](#the-two-modes)
- [The `.handoff/` bundle format](#the-handoff-bundle-format)
- [Sender workflow](#sender-workflow)
- [Recipient workflow](#recipient-workflow)
- [Security posture](#security-posture)
- [Bundled scripts](#bundled-scripts)
- [Install](#install)
- [Usage](#usage)
- [Requirements & limitations](#requirements--limitations)
- [File layout](#file-layout)

---

## Why this exists

Copying a folder, a `CLAUDE.md`, and a `.claude/` directory produces a project that is
*configured* — not one that is *understood*. A real handoff succeeds when the new owner can
make autonomous decisions: they know why the architecture is the way it is, what is fragile,
what is taboo, and what is only half-built.

A Claude Code project is a **bundle of visible artifacts** (code, git history, `CLAUDE.md`,
`.claude/`) **plus invisible context**. That invisible context splits into three fates:

| Layer | Examples | Fate |
|-------|----------|------|
| Versioned artifacts | code, git history, backlog, plans | **Portable** — git already moves it |
| Project config | `CLAUDE.md`, in-repo `.mcp.json` | **Portable with sanitization** — absolute paths, hooks, and env references need auditing |
| Environment & deps | runtime, toolchain, MCP servers, external services | **Reconstructable** — a *manifest of needs* travels, not the installations |
| Account/machine state | API keys, connectors, personal global config, memory | **Reconstructable-as-needs, never portable-as-values** |
| Tacit knowledge | rationale, state of play, gotchas, stakeholders | **Teachable** — exists in no file; must be extracted |

Git already solves the first layer. The value of this skill is the reconstructable and
teachable layers — and especially the tacit one, which no existing tool captures.

Part of what the skill produces is not information *about* the project — it is a
**behavioral protocol for the other agent**. It is therefore designed as a versioned,
inspectable, consent-gated exchange format, not as a side effect of copying files.

---

## The two modes

The skill decides which side you are on from your request; if genuinely ambiguous it asks
once.

### Sender — `/claude-to-claude handoff [<project-path>]`
You are giving a project away. Claude conducts an **exit interview**, mines the project,
sanitizes it, and assembles the handoff bundle. **The interview is mandatory** — mining only
pre-fills the questions; the tacit knowledge is the point.

### Recipient — `/claude-to-claude onboard [<project-path>]`
You received a project containing a `HANDOFF.md` / `.handoff/`. Claude verifies the bundle,
presents the inheritance, guides environment reconstruction with smoke tests, gives a
calibrated tour, proposes a low-risk first task, and drives the transition to **graduation**
— a designed end where the scaffolding is archived and the project becomes a normal Claude
Code project again.

The skill is also **auto-relevant** whenever a project contains a `HANDOFF.md` or `.handoff/`
directory at its root — so even a Claude *without* this skill installed can read `HANDOFF.md`
and give a coherent guided readout (degraded mode).

---

## The `.handoff/` bundle format

The bundle lives **inside the repo** so it travels with git and never goes stale relative to
the code. A root `HANDOFF.md` is the human-and-Claude-readable entry point; `.handoff/` holds
the structured, provenance-tagged knowledge pack.

```
<repo>/
├── HANDOFF.md                 # entry point — any Claude reads it on open (works without the skill)
└── .handoff/
    ├── manifest.yaml          # schema version, created date, SOURCE COMMIT (freshness stamp), sender contact
    ├── project-brief.md       # what the project IS: purpose, architecture, the owner's mental model
    ├── state-of-play.md       # works / in-progress / blocked / half-done
    ├── decision-log.md        # WHY key decisions were made
    ├── gotchas.md             # costly traps, fragile zones, "don't touch"
    ├── environment.md         # reconstructable needs: runtime, deps, MCP-by-need, secrets BY NAME ONLY, services
    ├── onboarding-protocol.md # behavioral script FOR the recipient's Claude
    └── known-unknowns.md      # sender-flagged uncertainties + return-channel contact
```

### Provenance tagging

Every non-trivial claim carries a tag so the recipient never mistakes an inference for a
fact:

- `[declared]` — stated by the departing owner in the exit interview.
- `[inferred]` — deduced by mining (git, code, backlog). May be wrong.
- `[uncertain]` — the owner explicitly flagged this as something they're unsure about.

The full manifest schema and rules are in [`references/bundle-format.md`](references/bundle-format.md).

---

## Sender workflow

Detailed procedure: [`references/sender-flow.md`](references/sender-flow.md).

1. **Scope & consent** — confirm the project and the ownership-transfer intent; capture the
   sender's contact (the light return channel for residual questions).
2. **Mine** — run `mine_project.py`, then read the high-signal sources it points at: project
   `CLAUDE.md`, any `SESSION_HANDOFF.md`, backlog/plans, the top-churned files, and the
   out-of-tree memory directory (which will *not* travel with a clone — distill it, don't copy).
3. **Generate targeted questions** from the gaps mining could not fill.
4. **Exit interview (mandatory)** — one question at a time: why the architecture, what's
   half-done, what's fragile, what's taboo, who the stakeholders are.
5. **Dependency discovery** — including hidden reliance on the sender's *global* skills/config
   the project used without declaring.
6. **Sanitize** — secret-scan (values → names), de-personalize, path-audit. See below.
7. **Assemble & review** — write the bundle with `assemble_bundle.py`, show the human, get
   consent, optionally commit.

---

## Recipient workflow

Detailed procedure: [`references/recipient-flow.md`](references/recipient-flow.md).

1. **Detect & verify** — run `verify_bundle.py`: structure completeness, manifest parse, a
   freshness check (drift between the packaged `source_commit` and current `HEAD`), and the
   sender's secret-scan claim. Treat the bundle as *untrusted input*.
2. **Present the inheritance** — no cold start: "you received this from X on <date>; here's
   what it is, where it stands, and what we'll do first."
3. **Reconstruct the environment** — walk `environment.md` as a live checklist: the recipient
   supplies *their own* secrets and MCP setup, each verified with a smoke test before it's
   ticked off.
4. **Guided tour** — architecture, key decisions *and their why*, top gotchas; calibrated to
   what the recipient already knows.
5. **First task** — a low-risk starter that touches the core without being able to break it.
6. **"Ask the project" mode** — answers grounded in the bundle + code, always separating
   declared from inferred.
7. **Graduation** — durable facts fold into the project's own `CLAUDE.md` and the recipient's
   memory; the `.handoff/` scaffolding is archived and removed. Onboarding has a designed end.

---

## Security posture

Full rules: [`references/security-posture.md`](references/security-posture.md) and
[`references/sanitization.md`](references/sanitization.md).

- **Secrets never travel.** The bundle references secrets by *name* and how to obtain them —
  never by value. The sender scans the repo *and* every piece of distilled tacit text with
  `scan_secrets.py` (patterns cover IBAN, private keys, `api_key/token=…`, OpenAI `sk-…`,
  Slack `xox…`, GitHub `ghp_…`, AWS keys, and `.env`-style assignments) before packaging.
- **The bundle is untrusted input.** On the recipient side the rule is `inspect → show →
  human consent → activate`. Bundled hooks, commands, and `.mcp.json` servers are **inert by
  default** — they are presented to the human, never auto-run.
- **Project ≠ person.** The sender's global `~/.claude/CLAUDE.md`, personal memory, aliases,
  and language preferences do **not** travel. The recipient's own global identity stays
  intact; project knowledge is grafted *on top* of it.
- **Freshness-aware.** `source_commit` lets the recipient detect drift; where the bundle and
  the code disagree, the code is ground truth.

---

## Bundled scripts

All scripts emit JSON to stdout and are pure plumbing — the interview, the tour, and the
graduation are conducted by Claude, which is why this is a skill and not a shell tool.

| Script | Side | Purpose |
|--------|------|---------|
| `scripts/mine_project.py` | sender | Gather signals: git-log digest, top-churned files, deps, in-repo `.mcp.json` (flags absolute paths), state files, and the out-of-tree memory dir. Emits interview-gap nudges. |
| `scripts/scan_secrets.py` | sender | Scan tracked files and/or a draft (`--text FILE`) for secret **values**. Redacts matches in its own report so the report never leaks. Non-zero exit if anything is flagged. |
| `scripts/assemble_bundle.py` | sender | Write `.handoff/` + `HANDOFF.md` from a spec JSON (`--spec`). Serializes `manifest.yaml`; no clock access (date/commit are passed in). |
| `scripts/verify_bundle.py` | recipient | Structure + manifest + freshness (drift vs `HEAD`) check. Read-only by design; flags untrusted-config surface without touching it. |

---

## Install

Via the repo's installer:

```bash
./install.sh
# select "claude-to-claude" from the skills list
```

Or manually — copy the skill into your Claude Code skills directory:

```bash
cp -r skills/claude-to-claude ~/.claude/skills/claude-to-claude   # global (all projects)
# or, project-scoped:
cp -r skills/claude-to-claude <your-project>/.claude/skills/claude-to-claude
```

The `SKILL.md` body invokes the scripts via absolute `~/.claude/skills/claude-to-claude/…`
paths; if you install project-scoped, adjust those paths accordingly.

---

## Usage

```text
# You are handing a project OFF:
"prepare a handoff of this project for <person>"
/claude-to-claude handoff ~/path/to/project

# You RECEIVED a project (it has a HANDOFF.md / .handoff/):
"I inherited this project, onboard me"
/claude-to-claude onboard ~/path/to/project
```

The skill responds in the language of your prompt.

---

## Requirements & limitations

- **Requirements:** Python 3 and git. No third-party Python packages (uses only the standard
  library). `verify_bundle.py` uses PyYAML if available and falls back to a minimal parser if
  not.
- **This packages knowledge, not accounts.** Transferring repository ownership/access
  (GitHub org, collaborators) and provisioning the recipient's own API keys and MCP servers
  are separate steps the skill guides but does not perform.
- **The tacit layer is only as good as the interview.** Skipping the exit interview degrades
  the bundle to a glorified `git clone`. The mining step never substitutes for it.
- **Snapshot semantics.** The bundle describes the repo at `source_commit`. If the repo moves
  on before ingest, `verify_bundle.py` reports the drift; prefer the code as ground truth.

---

## File layout

```
claude-to-claude/
├── SKILL.md                     # trigger + routes handoff vs onboard modes
├── README.md                    # this file
├── references/
│   ├── bundle-format.md         # .handoff/ schema + manifest spec + provenance rules
│   ├── sender-flow.md           # exit-interview + mining + sanitization procedure
│   ├── recipient-flow.md        # ingest + onboarding + graduation procedure
│   ├── sanitization.md          # secret-scan, de-personalization, path audit, project/person boundary
│   └── security-posture.md      # untrusted-bundle handling, consent gates, no-auto-hook rule
├── scripts/
│   ├── mine_project.py
│   ├── scan_secrets.py
│   ├── assemble_bundle.py
│   └── verify_bundle.py
└── assets/
    ├── HANDOFF.md.tmpl          # root entry-point template
    └── manifest.yaml.tmpl       # manifest schema skeleton
```
