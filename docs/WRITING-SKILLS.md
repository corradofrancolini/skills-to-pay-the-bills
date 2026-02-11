# Writing Your Own Skills

How to create custom Claude Code skills from scratch.

## Skill vs Command

| | Skill | Command |
|---|---|---|
| Location | `.claude/skills/<name>/SKILL.md` | `.claude/commands/<name>.md` or `~/.claude/commands/<name>.md` |
| Scope | Project-level | Project or global |
| Activation | Automatic (Claude loads as context when relevant) | Manual (`/<command-name>`) |
| Best for | Domain expertise, audits, workflows | On-demand utilities, one-shot actions |

## Skill Anatomy

```markdown
---
name: skill-name
description: One-line description of what this skill does
---

# Skill Title

One-line description of the specialized agent's role.

## Configuration

| Placeholder | Description | Example |
|---|---|---|
| `{{PLACEHOLDER}}` | What it controls | "Example value" |

## Context

Background information the agent needs to do its job.

## When to Invoke

- Trigger condition 1
- Trigger condition 2

## Actions

### 1. First Step
What to do and how.

### 2. Second Step
...

## Checklist (if applicable)
- [ ] Item 1
- [ ] Item 2
```

## Key Sections

### Frontmatter (required)

```yaml
---
name: kebab-case-name
description: Short description shown in skill listings
---
```

The `name` must match the folder name. The `description` helps Claude Code decide when the skill is relevant.

### Configuration (recommended for templates)

A table of all `{{PLACEHOLDER}}` tokens used in the skill, with descriptions and examples. This is the first thing users see when customizing.

### Context

Background the agent needs: tech stack, constraints, references to documentation files. Keep it factual and concise.

### When to Invoke

Bullet list of trigger conditions. These help Claude Code understand when to activate the skill. Be specific -- vague triggers lead to false activations.

### Actions

Step-by-step instructions. Number them. Each step should be a clear action:

1. **Gather information** -- what to ask the user or read from the codebase
2. **Execute** -- what to do (audit, generate, review, etc.)
3. **Report** -- how to present results
4. **Apply** -- how to make changes (always wait for confirmation)

### Checklists

For audit-type skills. Use markdown checkboxes. Group by category. Reference standards where applicable (WCAG criteria, performance metrics, etc.).

## Design Principles

### Be specific, not generic

Bad: "Review the code for issues"
Good: "Check that all async functions have try/catch blocks around external API calls"

### Define the output format

Tell Claude exactly how to present results. Use code blocks with example output. This ensures consistency across invocations.

### Wait for confirmation before changes

Always include a step like "Propose changes and **wait for confirmation** before applying them." This prevents the agent from making unwanted modifications.

### Keep skills focused

One skill = one concern. A skill that does accessibility AND performance AND SEO is three skills. Split them.

### Use optional sections for variants

If a skill has project-specific steps that not everyone needs, wrap them in HTML comments:

```markdown
<!-- optional: description -->
<!--
### Optional Step
Instructions here.
-->
```

## Command Anatomy

Commands are simpler -- no frontmatter, just markdown instructions:

```markdown
Description of what the command does.

## Instructions

1. Step 1
2. Step 2
3. Step 3

## Notes
- Note 1
- Note 2
```

Commands are invoked with `/<name>` in Claude Code. They are best for utilities that the user triggers manually.

## Tips

- **Test your skill** by asking Claude Code to use it. If it misunderstands the instructions, the skill needs clearer wording.
- **Iterate on the Actions section** -- this is where most confusion happens. Be explicit about what to ask the user, what to read, and what to output.
- **Reference real files** with `{{PLACEHOLDER}}` paths so the skill knows where to look in the codebase.
- **Keep checklists actionable** -- each item should be something Claude can verify by reading code, not something that requires human judgment.
