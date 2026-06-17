# Authoring guide — content.md

How to write the `content.md` that `build_report.py` turns into a house-format report.
This is the **stable contract**: a human writes it today, a future generator emits it tomorrow.

## Front-matter (flat scalars only)

```yaml
---
title: Models Migration — Tier 1 + Tier 2 Results
date: 2026-05-29
author: Websolute AI team
subtitle: Environment DEV · CEST            # optional
footer: Internal report · Websolute         # optional
lang: en                                    # optional (default en)
toc: true                                   # optional (default true)
client: efg                                 # optional — short slug; groups the report under a client in a reports hub. Default: misc
tags: timeout, repro, investigation         # optional — comma-separated; shown in the auto-generated index
summary: One-line plain-text TL;DR shown on the hub index card.   # optional
---
```
No nested YAML. The meta line shown under the title is `date · author · subtitle` (present ones).

`client` / `tags` / `summary` do NOT affect the report body — they feed the **auto-generated index** of a reports hub. `client` is a free-form slug used only for grouping. Each build also writes a `<name>.meta.json` sidecar next to the HTML (machine-readable: title/date/author/subtitle/client/tags/summary/html_filename) — the index source; it doesn't touch the self-contained HTML.

## Body — standard Markdown

`##` / `###` headings (auto-assigned ids; `##` populate the sidebar TOC), `| pipe | tables |`,
lists, `code`, fenced ```code blocks```, [links](https://…), **bold**, _italic_.

## Shortcodes (rich blocks)

### TL;DR
```
::: tldr
[Scope]{.label .label-scope} what was tested.

[Tier 1]{.label .label-t1} 37/37 PASS.

[Verdict]{.label .label-verdict} drop-in is EASY — no regressions.
:::
```
Label variants: `.label-scope .label-t1 .label-t2 .label-t3 .label-verdict`. A paragraph whose
label is `.label-verdict` automatically becomes the dashed-top `.verdict-line`.

### Callouts
```
::: callout
**Why this matters**
Explanation text here.
:::

::: {.callout .callout-green}
**Resolved**
Green variant. Also `.callout-blue`, `.callout-red`.
:::
```
A leading `**Title**` line becomes the `.ct-title`.

### Inline badges & status
```
[PASS]{.ok}  [partial]{.warn}  [FAIL]{.bad}
[Preview]{.badge .badge-preview}  [Stable]{.badge .badge-stable}
```
Badge variants: `.badge-preview .badge-stable .badge-critical .badge-tier1 .badge-tier2 .badge-tier3`.
Use `[text]{.ok}` etc. inside table cells too.

> **Gotcha:** a bracketed span does NOT render inside inline-code backticks. `` `foo [Stable]{.badge .badge-stable}` `` stays literal text. Put the span outside the backticks: `` `foo` `` [Stable]{.badge .badge-stable}.

### Conversation evidence / bespoke blocks → raw HTML
Markdown can't express collapsible transcripts, so write them as raw HTML. **Two rules** so
pandoc passes them through verbatim:
1. **Flush-left** — no leading indentation on any line (4+ spaces = Markdown indented code block → your HTML gets escaped).
2. **No blank lines inside** the block (a blank line ends the raw-HTML block).
Surround the whole block with blank lines.

```html
<details>
<summary><code>TEST_001</code> · 1t · 14s · bot <span class="q-pill">user question snippet…</span></summary>
<div style="padding:0.7rem 1rem;">
<p><strong>Final answer:</strong></p>
<pre style="white-space:pre-wrap;">bot answer…</pre>
</div>
</details>
```
Per-block copy icons are injected at runtime by the report JS — you do **not** add any copy markup.

## Build
```bash
python3 ~/.claude/skills/html-report/scripts/build_report.py content.md --out report.html
```
Output is one self-contained `.html` (CSS/JS/favicon inlined). Open it or publish via temp-pub.
