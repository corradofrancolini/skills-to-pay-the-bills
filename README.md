# Skills to Pay the Bills

Ready-to-use skill and command templates for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Each template is a standalone `.md` file with `{{PLACEHOLDER}}` tokens you replace with your project-specific values. Pick the ones you need, install them, fill in the blanks.

## Catalog

### Skills (project-level)

| Skill | Category | Description |
|-------|----------|-------------|
| [accessibility](skills/accessibility/) | Quality | WCAG 2.1/2.2 Level AA audits with checklists and visual fix picker |
| [content](skills/content/) | Content | Microcopy review, tone of voice, error/success messages, alt text, meta tags |
| [creative](skills/creative/) | Process | Divergent exploration methodology to counter premature convergence |
| [design-system](skills/design-system/) | Quality | Design token and component consistency checks |
| [project-index](skills/project-index/) | Utility | Generates a visual text-based map of the project |
| [review](skills/review/) | Quality | Code review checklists for correctness, security, performance, a11y |
| [seo](skills/seo/) | Quality | SEO and Core Web Vitals audits |
| [session-end](skills/session-end/) | Process | Session handoff documentation for continuity between sessions |

### Commands (global)

| Command | Description |
|---------|-------------|
| [project-index](commands/project-index.md) | Same as the skill, but installed globally for all projects |

## Quick Start

### Option A: Interactive installer

```bash
git clone https://github.com/YOUR_USERNAME/skills-to-pay-the-bills.git
cd skills-to-pay-the-bills
./install.sh /path/to/your/project
```

The installer lets you pick which skills to install and reports which `{{PLACEHOLDERS}}` you need to fill in.

### Option B: Manual install

1. Copy a skill folder into your project:

```bash
# Install a skill
cp -r skills/review/ /path/to/your/project/.claude/skills/review/

# Or install a global command
cp commands/project-index.md ~/.claude/commands/project-index.md
```

2. Open the `SKILL.md` file and replace all `{{PLACEHOLDER}}` values with your project's specifics. Each skill has a **Configuration** table at the top listing every placeholder with its description and an example value.

## How Skills Work

**Skills** live in `.claude/skills/<name>/SKILL.md` inside a project. Claude Code automatically loads them as context when relevant. Each skill has:

- A YAML frontmatter with `name` and `description`
- A `## Configuration` table listing all placeholders
- `## When to Invoke` triggers
- `## Actions` with step-by-step instructions
- Optional checklists for audit-type skills

**Commands** live in `~/.claude/commands/` (global) or `.claude/commands/` (project). They are invoked explicitly with `/<command-name>`.

See [docs/WRITING-SKILLS.md](docs/WRITING-SKILLS.md) for the full anatomy and how to write your own.

## Customization

Every template uses `{{DOUBLE_CURLY}}` placeholders in `ALL_CAPS_SNAKE_CASE`. The **Configuration** table at the top of each skill lists them all.

Some skills also have optional sections wrapped in HTML comments (`<!-- optional: ... -->`). Uncomment the ones you need, delete the ones you don't.

See [docs/CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for a detailed guide.

## Docs

- [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) -- How to adapt templates to your project
- [WRITING-SKILLS.md](docs/WRITING-SKILLS.md) -- How to write your own skills from scratch

## License

[MIT](LICENSE)
