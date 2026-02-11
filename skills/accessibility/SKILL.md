---
name: accessibility
description: WCAG 2.1/2.2 Level AA accessibility audits
---

# Accessibility Audit

Specialized agent for web accessibility. Verifies conformance to WCAG 2.1/2.2 Level AA.

## Configuration

| Placeholder | Description | Example |
|---|---|---|
| `{{UI_COMPONENT_LIBRARY}}` | Your accessible component library (if any) | "Radix", "Ariakit", "shadcn/ui", "native HTML" |
| `{{WCAG_TARGET}}` | Target WCAG conformance level | "WCAG 2.1/2.2 Level AA" |

## Context

- **Component library**: {{UI_COMPONENT_LIBRARY}}
- **Target**: {{WCAG_TARGET}}

## When to Invoke

- Before releasing a page or component
- After significant UI changes
- For periodic audits
- When adding multimedia content

## Actions

### 1. Identify Scope

Ask the user what to verify:
- **Component**: file name
- **Page**: route
- **Entire site**: full audit

### 2. Execute Audit

Use the checklist below. For each section, verify the applicable criteria.

### 3. Report

```
## Accessibility Audit

**Scope**: [component/page]
**Date**: [date]
**Target level**: {{WCAG_TARGET}}

### Results

| Category | Pass | Fail | N/A |
|----------|------|------|-----|
| Visual Design | 12 | 2 | 3 |
| Interactions | 8 | 0 | 5 |
| ...

### Issues Found

#### [Critical] 1.4.3 - Insufficient contrast
- **Where**: Ghost button on light background
- **Problem**: Ratio 2.8:1, required 4.5:1
- **Proposed fix**: Change text color from #999 to #666

#### [Medium] 2.4.4 - Non-descriptive link label
- **Where**: Footer, "Click here" link
- **Proposed fix**: Change to "Go to Academy page"
```

### 4. Visual Fix Picker

Generate a standalone HTML page to visualize each issue with real components and fix options side by side, allowing the user to visually choose the preferred solution.

**Output**: `$SCRATCH/audits/accessibility-fixes-visual.html`

**Page structure**:
- Header with title and legend
- Card for each identified issue
- Each card contains:
  - Issue title + WCAG criterion
  - Problem description
  - Grid with options: **Current** | **Fix A** | **Fix B** | ...
  - Component rendered in each cell with the project's styles
  - Descriptive label under each option

**Technologies**:
- Standalone HTML (no build step)
- CSS framework CDN (adapt to your project)
- Project fonts via CDN or local reference
- Custom CSS with your project palette
- Vanilla JavaScript for interactive selection (optional)

<!-- CUSTOMIZE: Adapt the HTML template to your project's fonts and colors -->

**Example card structure**:
```html
<div class="issue-card">
  <h3>[Critical] 1.4.1 -- Links not distinguishable without color</h3>
  <p>Links rely solely on color to be distinguished from surrounding text.</p>

  <div class="options-grid">
    <div class="option current">
      <div class="preview">Explore &rarr;</div>
      <span class="label">Current (color only)</span>
    </div>
    <div class="option fix-a">
      <div class="preview"><u>Explore &rarr;</u></div>
      <span class="label">Fix A: always underline</span>
    </div>
    <div class="option fix-b">
      <div class="preview"><b>Explore &rarr;</b></div>
      <span class="label">Fix B: bold + arrow</span>
    </div>
  </div>
</div>
```

**After generation**: open the file in the browser for visual review.

### 5. Propose Fixes

Propose specific changes and **wait for confirmation** before applying them.

---

# Accessibility Checklist

## Visual Design

### Color Guidelines

- [ ] **1.4.1** Color is NOT the only means of conveying information (errors, states, charts)
- [ ] **1.4.3** Text contrast:
  - 4.5:1 for text < 24px (or < 19px bold)
  - 3:1 for text >= 24px (or >= 19px bold)
- [ ] **1.4.11** Non-text UI components: at least 3:1 against borders and adjacent colors
- [ ] **1.4.11** Visible focus state: at least 3:1 against background
- [ ] Color combinations documented for each state (success, error, warning, info)

### Text Resizing & Typography

- [ ] **1.4.4** Text enlargeable to 200% without loss of content/functionality
  - No fixed heights on buttons
  - No overflow: hidden on text boxes
  - Layout adapts to large fonts
  - Hierarchy maintained (H1 > H2 > H3...)
  - No truncation when text grows
- [ ] **1.4.12** Custom text spacing support:
  - Line height at least 1.5x font size
  - Paragraph spacing at least 2x font size
  - Letter spacing at least 0.12x font size
  - Word spacing at least 0.16x font size

### Typography Best Practices

- [ ] Text is selectable (for translations, copying)
- [ ] Avoid ultra-light and light font weights
- [ ] Avoid justified text, prefer left alignment
- [ ] Content width limited (~80 characters for Latin scripts)
- [ ] Avoid italic and ALL CAPS for long passages
- [ ] Underline only for links
- [ ] Readable font: distinguishable characters (iIlL10oO)

## Interactions

### Buttons & Links

- [ ] **1.4.1** Links in text blocks distinguishable not only by color (underline)
- [ ] **2.4.4** Clear and descriptive labels -- user understands what happens on click
- [ ] **3.2.4** Same destination = same consistent label
- [ ] **1.3.3** Avoid instructions based on shape/color ("click the red button")
- [ ] File links: indicate format and size
- [ ] **3.2.5** Avoid opening in new tab; if necessary, warn the user
- [ ] Link states documented: default, hover, focus, active, visited
- [ ] Button states documented: default, hover, focus, active, disabled, selected, loading
- [ ] **2.5.8** Target size at least 24x24 CSS pixels
- [ ] **2.5.5** Mobile touch target at least 44x44 CSS pixels (AAA)
- [ ] Spacing between touch targets at least 8px

### Forms & Inputs (3.3)

- [ ] Form states documented: default empty, default filled, focused, disabled, checked, unchecked
- [ ] Status states documented: default, error, success, warning, info
- [ ] **1.3.1** All fields have a visible (or programmatic) label
- [ ] Label connected to field (for + id)
- [ ] Label is NOT a placeholder
- [ ] **3.3.2** Clear label on how to fill the field
- [ ] Label close to the field
- [ ] **3.2.4** Consistent labels across the interface
- [ ] **3.3.2** Required fields indicated
- [ ] **3.3.2** Expected format clear (with examples)
- [ ] **3.3.4** For legal/financial data: ability to reverse, review, confirm
- [ ] **1.4.1** Errors NOT shown only with color
- [ ] **3.3.1** Clear and understandable error messages
- [ ] **3.3.3** Correction suggestions offered
- [ ] **3.3.7** Do not require the same input twice in a session
- [ ] **3.3.8** Authentication: allow copy/paste passwords, 2FA, biometric
- [ ] **1.3.1** Related fields grouped visually and programmatically

## Focus & Keyboard Navigation

### Skip Links

- [ ] **2.4.1** Skip link present to bypass repeated content (nav)
- [ ] Skip link is the first focusable element on the page

### Focus Order

- [ ] Focus state documented for interactive elements
- [ ] **2.4.3** Logical focus order at page level
- [ ] **2.4.3** Logical focus order at component level
- [ ] **2.1.2** No focus trap (user can always exit)
- [ ] **2.4.11** Focused element never fully covered by other content

### Component Interactions

- [ ] **2.1.1** All interactive elements reachable and activatable via keyboard
- [ ] **3.2.1** No context change on focus (only on activation)
- [ ] **2.4.3** Meaningful focus order within component
- [ ] **1.4.13** Component dismissible without moving focus (e.g., Escape)
- [ ] **2.1.2** No keyboard trap
- [ ] **1.4.13** Content on hover/focus: dismissible, persistent, does not disappear

### Gestures & Dragging

- [ ] **2.5.1** Alternatives to complex gestures (multi-finger, path-based)
- [ ] **2.5.1** Single-pointer alternative for dragging
- [ ] **2.5.4** UI alternative for motion actuation (device shake, etc.)
- [ ] Visual indication for horizontal scroll

## Navigation & Wayfinding

### Screen Reader Order

- [ ] **1.3.2** Reading order documented if different from visual (rare case)

### Cross-Page Navigation

- [ ] **3.2.3** Consistent navigation across the site
- [ ] **2.4.5** Multiple ways to find content (nav + search, nav + sitemap)
- [ ] **3.2.6** Help function in consistent position

### Headings

- [ ] **2.4.6** Consistent and descriptive headings
- [ ] **1.3.1** Logical heading order (no h2 after h3)
- [ ] **1.3.1** Use Hn tags, not paragraphs styled as headings
- [ ] **1.3.1** Do not use headings for styling
- [ ] One h1 per page
- [ ] No skipping levels (h1 -> h4)

### Titles & Landmarks

- [ ] **2.4.2** Informative and unique HTML title per page
- [ ] **1.3.1** Landmark regions identified (header, nav, main, footer)

## Content

### Screen Reader Access

- [ ] **1.1.1** Screen reader can navigate all content
- [ ] **1.4.5** Text used instead of images of text
- [ ] **1.1.1** Alternatives for non-text content

### Images

- [ ] **1.1.1** Alt text for non-decorative images
- [ ] **1.1.1** Alt text for icons without visible label
- [ ] Detailed description for complex images (infographics, data viz)

### Multimedia

- [ ] Avoid media autoplay
- [ ] **1.2.1** Transcript for audio-only
- [ ] **1.2.1** Description/audio track for video-only
- [ ] **1.2.2** Captions for video with audio
- [ ] **1.2.3** Descriptive text alternative for video
- [ ] **1.2.5** Audio description for video (AA)
- [ ] **1.2.4** Captions for live audio
- [ ] **1.4.2** Control for audio that starts automatically (>3s)
- [ ] **1.3.3** Visual alternative for audio information

### Charts & Graphs

- [ ] **1.4.1** Information not conveyed solely through color
- [ ] **1.4.3** Text in charts with sufficient contrast
- [ ] **1.4.11** Chart elements with 3:1 against adjacent
- [ ] **1.1.1** Text alternative for charts
- [ ] Keyboard navigation for interactive charts

### Tables

- [ ] **1.3.1** Simple tables: caption + row/column headings
- [ ] **1.3.1** Complex tables: caption + headings + summary
- [ ] Row/column navigation with assistive tech
- [ ] NO tables for layout

### Screen Orientation

- [ ] **1.3.4** Do not lock orientation change
- [ ] Support portrait and landscape
- [ ] Content visible in both orientations

### Motion & Flashing

- [ ] **2.2.2** Control for moving content (>5s): play/stop/hide
- [ ] **2.3.3** Reduced-motion alternative for animations
- [ ] **2.3.1** No flash >3 times/second

### Time Limits

- [ ] **2.2.1** Time limit control: suppressible, extendable, or 20s warning

### Notifications & Status

- [ ] Choice of notification mode (visual, sound, vibration)
- [ ] **4.1.3** Screen reader informed of content/layout changes
- [ ] Page/popup transitions identified for screen reader
