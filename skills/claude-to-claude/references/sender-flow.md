# Sender flow — `/claude-to-claude handoff`

You are helping the **departing owner** package a project for a new owner. Your job is an
**exit interview + evidence gathering**, not a file copy. Work through these steps in order.
Reply in the user's language.

## Step 0 — Scope & consent

1. Confirm the target project path (default: current working dir; accept an explicit path).
2. Confirm intent out loud: "This packages **<project>** to hand OWNERSHIP to someone else,
   who will run it autonomously. It writes a `HANDOFF.md` + `.handoff/` into the repo. OK?"
3. Confirm who the recipient is (optional) and get the **sender contact** for the light
   return channel (email/handle). This is required — it's the fallback for residual Q&A.

Do not proceed without this confirmation.

## Step 1 — Mine (pre-fill, don't replace, the interview)

Run the miner and read its JSON:

```
python3 ~/.claude/skills/claude-to-claude/scripts/mine_project.py <project-path>
```

It reports: repo stats, a git-log digest (recent + most-churned files), branches, detected
dependency manifests, an in-repo `.mcp.json` (if any), backlog/plans presence, existing
`SESSION_HANDOFF.md`, the project `CLAUDE.md`, and a pointer to the **out-of-tree memory
dir** (`~/.claude/projects/<slug>/memory/`) if one exists for this project path.

Then read, yourself, the high-signal sources the miner points at:
- the project `CLAUDE.md` and any `SESSION_HANDOFF.md` / `docs/**` state files,
- the memory dir's `MEMORY.md` + notes (rich tacit knowledge — **distill**, never copy),
- `backlog/` tasks and `plans/` if present,
- the top-churned files to understand the architecture's center of gravity.

The memory dir is the **silent-dependency trap**: it lives outside the repo, is path-keyed,
and will NOT travel with a clone. Whatever is durable and project-relevant there must be
distilled into the bundle (secret-scanned, provenance-tagged `[inferred]` or `[declared]`
as appropriate).

## Step 2 — Generate targeted interview questions

From the gaps mining could NOT fill, draft a focused question set. Prioritize what no
artifact reveals:
- **Why** the core architectural choices (not what — the code shows what).
- What is **half-done** or intentionally stubbed, and what was the plan.
- What is **fragile** — what breaks often, what has bitten you.
- What is **taboo** — "don't touch X" / "never run Y in prod".
- **Stakeholders** — who depends on this, who to ask, who to notify.
- What you'd **do differently** / known debt.
- Any **known-unknowns** — things even you are unsure about.

## Step 3 — Conduct the exit interview (MANDATORY, one question at a time)

Ask **one question per turn**. Prefer concrete, answerable prompts seeded with what you
mined ("I see `retry.py` wraps every upstream call — why the retry, and what's the failure
it's guarding against?"). Record each answer tagged `[declared]`; when the owner hedges,
tag it `[uncertain]` and also add it to the known-unknowns list.

Keep it tight (aim ~10–20 minutes of the owner's time). The owner may say "skip" on a
question, but do not skip the interview as a whole — if they try, explain that without it
the bundle degrades to a glorified `git clone` and confirm they really want a thin bundle.

## Step 4 — Dependency discovery (including hidden global deps)

Beyond in-repo manifests, actively look for **hidden reliance on the sender's global
setup** that the project used without declaring:
- global skills/commands/agents the workflow depended on (ask: "which of your `/commands`
  or skills do you use *on this project* routinely?"),
- global MCP/connectors the project assumed were present,
- tools/CLIs installed globally (from `CLAUDE.md`, scripts, README).

Record these in `environment.md` as reconstructable needs — the recipient must set up their
own equivalents.

## Step 5 — Sanitize (red line)

Follow `references/sanitization.md`. Concretely:

1. Secret-scan the repo AND every piece of distilled tacit text you're about to write:
   ```
   python3 ~/.claude/skills/claude-to-claude/scripts/scan_secrets.py <project-path> --text <draft-file>
   ```
   If anything is flagged, replace values with named placeholders and re-scan until clean.
2. De-personalize: ensure NO content from the sender's global `~/.claude/CLAUDE.md`,
   personal memory, aliases, or language prefs leaks into the bundle. Project facts only.
3. Path audit: swap machine-absolute paths (e.g. in a copied `.mcp.json` note) for
   placeholders like `<REPO_ROOT>` / `<YOUR_HOME>`.

## Step 6 — Assemble & review

1. Compose the eight knowledge files + manifest from the interview + mining, with provenance
   tags throughout. Optionally designate a **first task** (a low-risk starter for the new
   owner).
2. Write the bundle:
   ```
   python3 ~/.claude/skills/claude-to-claude/scripts/assemble_bundle.py <project-path> --spec <spec.json>
   ```
   (Pass today's date and the resolved `source_commit`; the script cannot read the clock.)
3. Show the human the generated `HANDOFF.md` + a listing of `.handoff/`. Get explicit
   consent before committing anything.
4. On approval, optionally `git add .handoff HANDOFF.md && git commit`. Remind the owner to
   transfer repo ownership/access separately (this skill packages knowledge, not accounts).

## Output to the user at the end

- Where the bundle is and what it contains.
- The provenance summary (how much is declared vs inferred vs uncertain).
- Confirmation the secret scan is clean and no personal/global config was included.
- The one thing they should tell the recipient in person, if anything.
