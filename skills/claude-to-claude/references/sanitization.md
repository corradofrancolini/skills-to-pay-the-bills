# Sanitization & the project/person boundary

The bundle is about to leave your machine and enter someone else's project. Two failures
must be prevented: **leaking secrets** and **imposing the sender's personal setup on the
recipient**. Both happen silently if you don't actively guard against them.

## 1. Secrets — absolute red line

**No credential value ever travels.** The bundle references secrets by NAME and by how to
obtain them, never by value.

Run the scanner over the repo AND over every draft of distilled tacit text (interview
notes, decision log, memory distillations — these are a classic leak channel):

```
python3 ~/.claude/skills/claude-to-claude/scripts/scan_secrets.py <project-path>            # scan tracked files
python3 ~/.claude/skills/claude-to-claude/scripts/scan_secrets.py <project-path> --text <draft.md>  # scan a draft
```

It detects (patterns shared with `file-curator/detect_sensitive.py`): IBAN, Italian Codice
Fiscale, private-key blocks, generic `api_key/secret/token = <value>`, OpenAI-style `sk-…`,
Slack `xox…`, GitHub `ghp_…`, and `.env`-style assignments.

If anything is flagged:
1. Replace the value with a named placeholder: `OPENAI_API_KEY=<set-your-own>`.
2. Note in `environment.md`: the name, what it's for, and where to get it.
3. Re-scan until the report is `clean`. A bundle with a non-clean scan must NOT be shared.

Never include: `~/.env` contents, `.git/` credential helpers, `settings.local.json` tokens,
cloud session files, or raw transcripts (distill instead — opt-in only for a specific quoted
excerpt, and scan it).

## 2. The project/person boundary — what must NOT travel

Person-level config belongs to the sender as a *human*, not to the *project*. Carrying it
would impose the sender's way of working on the recipient. **Exclude:**

| Excluded (person-level) | Why |
|---|---|
| `~/.claude/CLAUDE.md` (global personal instructions) | The sender's cross-project prefs, language, house conventions — not this project's. |
| The out-of-tree memory dir contents, verbatim | Path-keyed personal memory; **distill** project-relevant facts, don't copy the files. |
| Personal aliases, shell config, global `/commands` & skills | The recipient has their own. Reference *needs*, not the sender's copies. |
| Global MCP/connector state, OAuth tokens | Per-user/per-client and secret. Recipient re-auths their own. |

**Include (project-level):** the repo, project `CLAUDE.md`, in-repo `.mcp.json` (path-audited),
backlog/plans, and the distilled knowledge pack.

Litmus test for any candidate item: *"Is this true about the PROJECT, or about the SENDER?"*
Only project-truths travel.

## 3. Path audit

Machine-absolute paths break on the recipient's machine. Before packaging, swap them for
placeholders in anything you write into the bundle (especially a copied `.mcp.json` snippet
or setup notes):

- `/Users/<sender>/Projects/Foo` → `<REPO_ROOT>`
- `/Users/<sender>/...` → `<YOUR_HOME>/...`

Flag in `environment.md` that an in-repo `.mcp.json` may contain absolute `cwd`/`PYTHONPATH`
the recipient must adjust.

## 4. Final pre-share gate

Before telling the user the bundle is ready, confirm ALL of:
- [ ] `scan_secrets.py` reports `clean` on repo and on every knowledge file.
- [ ] No person-level config (table above) is present in the bundle.
- [ ] Absolute paths are placeholdered.
- [ ] `manifest.yaml.sanitization` reflects the above (`secret_scan: clean`,
      `depersonalized: true`, `paths_placeholdered: true`).

If any box is unchecked, do not present the bundle as shareable.
