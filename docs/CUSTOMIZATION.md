# Customization Guide

How to adapt the skill templates to your project.

## Placeholder Syntax

All templates use `{{PLACEHOLDER_NAME}}` -- double curly braces with `ALL_CAPS_SNAKE_CASE` names.

Each skill has a **Configuration** table at the top listing every placeholder:

```markdown
## Configuration

| Placeholder | Description | Example |
|---|---|---|
| `{{TECH_STACK}}` | Your project's tech stack | "Next.js 15, React 19, Tailwind 4" |
```

## Step-by-Step

1. **Copy the skill** to your project's `.claude/skills/` directory
2. **Read the Configuration table** to see all placeholders
3. **Replace each placeholder** with your project's values
4. **Review optional sections** (see below)
5. **Test it** by asking Claude Code to invoke the skill

## Optional Sections

Some skills have sections wrapped in HTML comments:

```markdown
<!-- optional: session log -->
<!-- Uncomment the section below if your project keeps session logs -->

<!--
### 3. Update Session Log
...
-->
```

- **To enable**: remove the `<!--` and `-->` markers
- **To remove**: delete the entire commented block
- **To keep for later**: leave as-is (Claude Code ignores HTML comments)

## Placeholder Reference

Here are all placeholders used across the templates:

### Universal

| Placeholder | Used in | Description |
|---|---|---|
| `{{PROJECT_ROOT}}` | session-end | Absolute path to project root |
| `{{TECH_STACK}}` | review | Full tech stack description |

### Design & UI

| Placeholder | Used in | Description |
|---|---|---|
| `{{CSS_FRAMEWORK}}` | design-system | CSS framework and token system |
| `{{UI_COMPONENT_LIBRARY}}` | accessibility, design-system | Accessible component library |
| `{{PALETTE}}` | design-system | Color palette values |
| `{{TYPOGRAPHY}}` | design-system | Font stack |
| `{{DESIGN_TOKENS_FILE}}` | design-system | Path to design tokens file |
| `{{COMPONENTS_DIR}}` | design-system | Path to UI components directory |

### Content & SEO

| Placeholder | Used in | Description |
|---|---|---|
| `{{PROJECT_DESCRIPTION}}` | content | Brief project description and audience |
| `{{LOCALE}}` | content | Target language for UI content |
| `{{TONE_REFERENCES}}` | content | Brands whose tone you admire |
| `{{TARGET_AUDIENCE}}` | seo | Your target audience |
| `{{FRAMEWORK}}` | seo | Your web framework |

### Audit Targets

| Placeholder | Used in | Description |
|---|---|---|
| `{{WCAG_TARGET}}` | accessibility | Target WCAG conformance level |

## Customization by Skill

### accessibility

The WCAG checklist is universal and needs no changes. You only need to set `{{UI_COMPONENT_LIBRARY}}` and `{{WCAG_TARGET}}`. The Visual Fix Picker section uses a neutral default style -- add your project's fonts and colors in the `<!-- CUSTOMIZE -->` section.

### content

Replace the tone of voice traits with your own. The default traits (Professional but accessible, Empathetic, Pragmatic, Innovative with ethics) are examples. Fill in the Glossary table with your project-specific terminology.

### creative

This skill is almost entirely project-agnostic. No placeholders needed. Works as-is.

### design-system

The most heavily templatized skill. Fill in all 6 placeholders with your design system's specifics.

### review

Set `{{TECH_STACK}}` and uncomment the stack-specific checklist sections relevant to your project (React/Next.js, Vue/Nuxt, Tailwind, TypeScript, Python).

### seo

Set `{{TARGET_AUDIENCE}}` and `{{FRAMEWORK}}`. Fill in the Keyword Targets table with your SEO strategy. Add framework-specific optimizations in the `<!-- CUSTOMIZE -->` sections.

### session-end

Set `{{PROJECT_ROOT}}`. Uncomment optional sections if your project uses session logs, changelogs, or creative direction docs.

### project-index

No placeholders. Works as-is. Optionally create a `.project-index.yaml` file in your project root to define a curated project map (see the skill for the YAML format spec).
