The user is about to close the session. Update the handoff files so the next session can pick up seamlessly.

## Required Actions

### 1. Verify/Create SESSION_HANDOFF.md

If `SESSION_HANDOFF.md` does not exist in the project root, create it with this structure:

```markdown
# Session Handoff

## Last Updated
[date and time]

## Current State
[3 lines max: what works / in progress / blocked]

## Last Work Completed
- [bullet points of work done]

## Next Step
[1 concrete action for the next session]

## Open Problems
- [list if any]

## Files Modified Today
| File | Change |
|------|--------|
| ... | ... |
```

### 2. Update SESSION_HANDOFF.md

Read `SESSION_HANDOFF.md` and update it with:

- **Last Updated:** current date and time
- **Current State:** 3-line summary of what works / in progress / blocked
- **Last Work Completed:** bullet points of work done in this session
- **Next Step:** 1 concrete action
- **Open Problems:** updated list
- **Files Modified Today:** table of files touched today

<!-- optional: session log -->
<!-- Uncomment the section below if your project keeps session logs in docs/sessions/ -->

<!--
### 3. Update/Create Session Log

If `docs/sessions/[TODAY'S-DATE].md` does not exist, create it using the template in `docs/sessions/TEMPLATE.md`.

If it exists, append the work done in this session.

Also update the **Last Session** field in SESSION_HANDOFF.md with a link to today's session log.
-->

<!-- optional: project-specific steps -->
<!-- Add your own project-specific handoff steps below. Examples: -->

<!--
### Update Changelog (if applicable)

If prompts, configs, or tracked artifacts were modified in this session:
- Add an entry in your changelog with date, what changed, why

### Update Creative Direction (if applicable)

If design decisions were made and matured in this session, transfer them
from scratch notes to the main creative direction document.

### Update Scratch Notes (if applicable)

If there are session notes not yet documented, add them to your scratch notes file.
-->

### 3. Confirm

After updating the files, confirm to the user:
- Which files were updated
- Brief state recap
- "You can close the session."
