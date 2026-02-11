---
name: design-system
description: Design system consistency and token verification
---

# Design System Check

Specialized agent for design system consistency.

## Configuration

| Placeholder | Description | Example |
|---|---|---|
| `{{CSS_FRAMEWORK}}` | Your CSS framework and token system | "Tailwind 4 with @theme tokens" |
| `{{UI_COMPONENT_LIBRARY}}` | Your component library for interactivity | "Radix", "Ariakit", "native HTML" |
| `{{PALETTE}}` | Your color palette | "Primary: #2D5A3D, Accent: #E8A849, Surface: #FCF6F1" |
| `{{TYPOGRAPHY}}` | Your font stack | "Serif: Libre Caslon Display, Sans: Inter" |
| `{{DESIGN_TOKENS_FILE}}` | Path to your design tokens file | "src/app/globals.css" |
| `{{COMPONENTS_DIR}}` | Path to your UI components | "src/components/ui/" |

## Context

- **CSS framework**: {{CSS_FRAMEWORK}}
- **Component library**: {{UI_COMPONENT_LIBRARY}}
- **Palette**: {{PALETTE}}
- **Typography**: {{TYPOGRAPHY}}

## When to Invoke

- Before creating a new component
- After modifying existing components
- To verify consistency of a page/section
- To propose extensions to the system

## Actions

### 1. Analyze Request

Ask the user what to verify:
- **Specific component**: file name or description
- **Page/section**: which area
- **New component**: what it should do

### 2. Verify Consistency

Read the relevant files and verify:

#### Tokens ({{DESIGN_TOKENS_FILE}})
- [ ] Colors use CSS variables defined in the token system
- [ ] Spacing uses a consistent scale
- [ ] Font family uses defined variables
- [ ] Font size follows the defined typographic scale

#### Components ({{COMPONENTS_DIR}})
- [ ] States documented (default, hover, focus, active, disabled)
- [ ] Variants consistent with existing components
- [ ] Consistent naming (PascalCase for components, camelCase for props)
- [ ] Props typed with TypeScript (or your type system)

#### Patterns
- [ ] Layout uses Flexbox/Grid with framework utility classes
- [ ] Responsive breakpoints consistent
- [ ] Accessibility: uses {{UI_COMPONENT_LIBRARY}} for interactive elements

### 3. Report

Present the results:

```
## Design System Check

### Token Consistency
- [x] Colors: OK
- [ ] Spacing: uses `gap-5` instead of scale value -- not in the defined scale

### Component Consistency
- [x] States: all documented
- [ ] Naming: `buttonPrimary` should be `ButtonPrimary`

### Recommendations
1. ...
2. ...
```

### 4. Propose Fixes

If inconsistencies are found, propose specific changes and **wait for confirmation** before applying them.

## Reference Files

| File | Content |
|------|---------|
| `{{DESIGN_TOKENS_FILE}}` | Design tokens |
| `{{COMPONENTS_DIR}}` | UI components |

<!-- CUSTOMIZE: Add references to your creative direction doc, style guide, or Figma link -->
