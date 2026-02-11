# Skills to Pay the Bills

Ready-to-use skill and command templates for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Each template is a standalone `.md` file with `{{PLACEHOLDER}}` tokens you replace with your project-specific values. Pick the ones you need, install them, fill in the blanks.

## Catalog

### Skills (project-level)

Skills are loaded automatically by Claude Code as ambient context. Install them in projects where they're relevant.

#### [accessibility](skills/accessibility/)

WCAG 2.1/2.2 Level AA audit. Walks through a comprehensive checklist covering visual design (contrast, color usage, text resizing), interactions (buttons, links, forms), keyboard navigation (focus order, skip links, traps), navigation (headings, landmarks, screen reader order), and content (images, multimedia, tables, motion). Generates a structured report with severity levels and proposed fixes. Includes a **Visual Fix Picker** -- a standalone HTML page that renders each issue side-by-side with fix options so you can visually compare before deciding.

Placeholders: `{{UI_COMPONENT_LIBRARY}}`, `{{WCAG_TARGET}}`

#### [content](skills/content/)

Microcopy and written content review. Covers buttons and labels (action verbs, click clarity, consistency), error messages (what went wrong, how to fix, non-blaming tone), success messages (confirm + next step), empty states (explain why, suggest action), image alt text (context, not just description, max 125 chars), and meta title/description (character limits, keyword placement, CTAs). Includes a configurable tone of voice section and a project glossary table.

Placeholders: `{{PROJECT_DESCRIPTION}}`, `{{LOCALE}}`, `{{TONE_REFERENCES}}`

#### [creative](skills/creative/)

Divergent exploration methodology based on Stuart Kauffman's Adjacent Possible. Designed to counter AI sycophancy -- the tendency to converge on "safe" solutions that maximize approval instead of exploring the space. Produces at least 3 directions per decision (Expected, Divergent, Radical), maps which doors close with each choice, and includes a post-rejection analysis framework. Does NOT choose -- presents the space and waits for an explicit execution trigger.

No placeholders. Works as-is.

#### [design-system](skills/design-system/)

Design token and component consistency checks. Verifies that colors use CSS variables from the token system, spacing follows the defined scale, typography uses defined fonts and sizes. Checks components for documented states (default, hover, focus, active, disabled), consistent naming (PascalCase components, camelCase props), typed props, and responsive breakpoints. Reports inconsistencies with specific fix proposals.

Placeholders: `{{CSS_FRAMEWORK}}`, `{{UI_COMPONENT_LIBRARY}}`, `{{PALETTE}}`, `{{TYPOGRAPHY}}`, `{{DESIGN_TOKENS_FILE}}`, `{{COMPONENTS_DIR}}`

#### [project-index](skills/project-index/)

Generates a visual text-based map of the project using box-drawing characters. If a `.project-index.yaml` file exists in the project root, uses it as a curated guide (shows only what the YAML defines, respects order and groupings). If not, scans the project structure automatically (max depth 3, grouped by type, ignoring node_modules/.git/dist etc.). Includes the `.project-index.yaml` format spec so you can create your own. Also available as a [global command](commands/project-index.md).

No placeholders. Works as-is.

#### [review](skills/review/)

Code review against checklists for correctness (logic, edge cases, error handling, types, null checks, async/await), performance (re-renders, memo, blocking operations, bundle size), security (hardcoded secrets, input validation, SQL injection, XSS, CSRF, auth), maintainability (naming, function length, SRP, DRY, magic numbers), and accessibility (semantic HTML, ARIA, keyboard nav, focus management). Reports issues by severity with file:line references and proposed fixes. Includes commented-out stack-specific sections for React/Next.js, Vue/Nuxt, Tailwind, TypeScript, and Python that you can uncomment.

Placeholders: `{{TECH_STACK}}`

#### [seo](skills/seo/)

SEO and web performance audit. SEO checklist covers meta tags (title, description, robots, canonical, OG, Twitter), headings (hierarchy, keyword placement), content (uniqueness, keyword density, alt text, internal links), technical SEO (URLs, sitemap, robots.txt, redirects, broken links), structured data (Schema.org in JSON-LD), and mobile (viewport, responsive, touch targets). Performance checklist covers Core Web Vitals (LCP < 2.5s, FID < 100ms, CLS < 0.1, TTFB < 0.8s, FCP < 1.8s), image optimization, JavaScript bundle size, CSS purging, caching, and compression. Includes a keyword targets table template.

Placeholders: `{{TARGET_AUDIENCE}}`, `{{FRAMEWORK}}`

---

### Commands (global)

Commands are invoked explicitly with `/<command-name>`. Install them globally in `~/.claude/commands/` -- they work on any project.

#### [project-index](commands/project-index.md)

Same as the [project-index skill](skills/project-index/) but installed globally. Useful if you want `/project-index` available across all your projects without installing the skill in each one.

#### [session-end](commands/session-end.md)

Invoked with `/session-end` when closing a session. Creates or updates a `SESSION_HANDOFF.md` file in the project root with: last updated timestamp, current state (3-line summary), work completed (bullet points), next step (1 concrete action), open problems, and files modified. The next session reads this file to pick up where you left off.

Optional sections (uncomment to enable):
- **Session log**: creates daily log files in `docs/sessions/` using a template
- **Changelog update**: tracks changes to prompts, configs, or other artifacts
- **Creative direction update**: transfers matured design decisions from scratch notes to the main document
- **Scratch notes update**: captures undocumented session notes

No placeholders.

## Quick Start

### Option A: Interactive installer

```bash
git clone https://github.com/corradofrancolini/skills-to-pay-the-bills.git
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
