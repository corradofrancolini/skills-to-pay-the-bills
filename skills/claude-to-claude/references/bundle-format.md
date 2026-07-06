# The `.handoff/` bundle format (v1)

The handoff bundle is a **versioned, inspectable exchange format**. It lives inside the
repo so it travels with git and never goes stale relative to the code. Treat it as a
contract between the sender's Claude and the recipient's Claude.

## Layout

```
<repo>/
├── HANDOFF.md                 # entry point — self-explanatory; ANY Claude reads it on open
└── .handoff/
    ├── manifest.yaml          # machine-readable metadata (schema below)
    ├── project-brief.md       # what the project IS: purpose, architecture, the owner's mental model
    ├── state-of-play.md       # works / in-progress / blocked / half-done
    ├── decision-log.md        # WHY key decisions were made
    ├── gotchas.md             # costly traps, fragile zones, "don't touch"
    ├── environment.md         # reconstructable needs: runtime, deps, MCP-by-need, secrets BY NAME ONLY, services
    ├── onboarding-protocol.md # behavioral script FOR the recipient's Claude
    └── known-unknowns.md      # sender-flagged uncertainties + return-channel contact
```

`HANDOFF.md` and `.handoff/` are generated from `assets/HANDOFF.md.tmpl` and
`assets/manifest.yaml.tmpl` by `scripts/assemble_bundle.py`.

## Provenance tagging (mandatory)

Every non-trivial claim in the knowledge files carries a provenance tag so the recipient
never mistakes an inference for a fact:

- `[declared]` — stated by the departing owner in the exit interview.
- `[inferred]` — deduced by mining (git, code, backlog). May be wrong.
- `[uncertain]` — the owner explicitly flagged this as something they're unsure about
  (also collected in `known-unknowns.md`).

Use inline tags, e.g.:

```markdown
- The retry wrapper exists because the upstream API rate-limits hard at 10 req/s `[declared]`.
- The `legacy/` module appears unused since 2025-11 `[inferred]`.
```

## `manifest.yaml` schema

```yaml
c2c_schema: 1                       # bundle format version
created: "2026-07-06"               # ISO date the bundle was assembled (passed in; scripts can't read the clock)
source_commit: "<full-sha>"         # HEAD at packaging time — the FRESHNESS STAMP
source_branch: "<branch>"
project_name: "<name>"
sender:
  name: "<departing owner name>"
  contact: "<email / handle>"       # the LIGHT RETURN CHANNEL for residual Q&A
recipient_hint: "<optional: who this is for>"
first_task: "<optional: sender-designated low-risk starter, or null>"
provenance_summary:
  declared: <int>                   # counts, for a trust-at-a-glance readout
  inferred: <int>
  uncertain: <int>
sanitization:
  secret_scan: "clean" | "flagged"  # MUST be clean before a bundle is shared
  scanned_at_commit: "<sha>"
  depersonalized: true              # sender global config confirmed excluded
  paths_placeholdered: true         # absolute paths swapped for placeholders
environment:
  requires_mcp: ["<server-need names>"]
  requires_secrets: ["<ENV_VAR names, no values>"]
  external_services: ["<service names>"]
status: "packaged" | "in_transition" | "graduated"
```

`status` is the transition lifecycle marker. It flips to `in_transition` when the recipient
starts onboarding and to `graduated` at the end (see recipient-flow.md), at which point the
bundle is archived and removed from the working tree.

## `HANDOFF.md` (root entry point)

Kept deliberately short and human-first so it works **even for a Claude without this skill
installed** (degraded mode). It states: this is a handoff, from whom, as of which commit,
where the full bundle is, the one-paragraph project summary, the current state, the
suggested first step, and the return-channel contact. It ends by inviting a recipient who
*does* have the skill to run `/claude-to-claude onboard`.

## Design rules

- **No secret values, ever** — `environment.md` lists secret *names* and how to obtain
  them, never the values themselves.
- **Self-containing** — the recipient should be able to act from the bundle alone; the
  return channel is a fallback, not a dependency.
- **Freshness-aware** — `source_commit` lets the recipient detect drift if the repo moved
  on between packaging and ingest.
- **Reversible** — everything the bundle adds is confined to `HANDOFF.md` + `.handoff/`, so
  graduation can cleanly remove it.
