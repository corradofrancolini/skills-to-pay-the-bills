---
name: html-report
description: >
  Render report CONTENT (a Markdown file with front-matter) into a fixed, self-contained
  "house format" HTML report — sidebar TOC, TL;DR, callouts, badges, collapsible conversation
  evidence, a 3-format copy/export button, and per-block copy icons — and optionally publish it
  via a temporary public URL. USE WHEN the user says "html-report", "/html-report", "make this
  into a report", "turn this into the house report format", "format this .md as our report",
  "publish this as a report", or hands over a Markdown draft to become the standard styled HTML
  report. NOT for arbitrary web pages or a plain markdown→html conversion.
---

# html-report

Generic publishing layer: turns report **content** into the fixed **house-format** HTML
(self-contained — CSS, JS and favicon are inlined; no external files). The format is **frozen**;
deviate from it ONLY when the user explicitly asks. Project-agnostic — no EFG/GS1/etc. coupling.

## Workflow

1. **Ensure a content.md exists** in the contract shape (see `references/authoring-guide.md`).
   If the user hands raw text/notes, write/normalize a `content.md` first (front-matter + body).
2. **Build:**
   ```bash
   python3 ~/.claude/skills/html-report/scripts/build_report.py <content.md> [--out out.html]
   ```
   It prints the absolute output path. Requires `pandoc` on PATH.
3. **Verify** (recommended for new reports): open the output in a headless browser and confirm
   chrome present, TOC auto-built, export CTA works, per-block copy icons inject, favicon loads
   (no `/favicon.ico` 404), and the file is self-contained. See the verification recipe below.
4. **Publish** (only if asked): reuse temp-pub — do not reinvent tunneling:
   ```bash
   bash ~/.claude/skills/temp-pub/scripts/launch-tunnel.sh <out.html>   # prints + clipboards URL
   bash ~/.claude/skills/temp-pub/scripts/stop-tunnel.sh                # when done
   ```
   Prefer placing the output in its own/clean folder so the tunnel doesn't expose siblings.

## Input contract (the stable seam)

Front-matter (flat scalars only): `title`, `date`, `author`, `subtitle`, `footer`, `lang`, `toc`, plus optional `client`, `tags`, `summary` (for hub indexing — `client` is just a string; default `misc`). Each build also writes a `<name>.meta.json` sidecar next to the HTML (machine-readable index metadata).
Body: Markdown + shortcodes. Full reference in `references/authoring-guide.md`. Summary:
- `::: tldr` … `:::` with `[Scope]{.label .label-scope}` lines (+ a `[Verdict]{.label .label-verdict}` line → auto `.verdict-line`).
- `::: {.callout}` / `::: {.callout .callout-green}` (also `-blue`, `-red`); a leading `**Title**` becomes `.ct-title`.
- Inline `[PASS]{.ok}` / `[warn]{.warn}` / `[bad]{.bad}` and `[Stable]{.badge .badge-stable}` (variants: `-preview -stable -critical -tier1 -tier2 -tier3`).
- Headings `##`/`###` get auto ids + the sidebar TOC (h2). Tables, lists, code, links: standard Markdown.
- **Conversation evidence** and any bespoke rich block: write as **raw HTML** (`<details><summary>… <span class="q-pill">Q…</span></summary>…<pre>transcript</pre></details>`), blank-line separated — it passes through verbatim.

A future domain producer (e.g. an EFG/GS1 run→report generator) only needs to emit a `content.md`
in this shape and call `build_report.py`. It must never touch the chrome assets.

## Fixed-format rule (deviate only on request)

The chrome lives in `assets/chrome.css`, `assets/report.js`, `assets/skeleton.html`,
`assets/favicon.png` and is inlined verbatim. `build_report.py` has **no styling parameters** — a
normal run cannot change the look. The ONLY deviation path is the explicit `--override-css` /
`--override-js` / `--favicon` flags. **Never pass overrides unless the user explicitly asks for a
format change.** If they do: copy the asset to a scratch file, edit the copy, pass the override —
never edit the default assets in place. See `references/house-format-spec.md`.

## Options

`--out <path>` (default: input basename `.html`) · `--no-toc` · `--override-css <file>` ·
`--override-js <file>` · `--favicon <png>`.

- `--inline-images` — embed `<img>` sources (http/https or local files) as data: URIs so the
  report is fully self-contained / offline. `--max-inline-kb N` (default 2048) leaves images
  bigger than that linked, to avoid a huge file.
- `--pdf [path]` — also render a PDF via headless Chromium (Playwright): expands all `<details>`
  and hides the interactive buttons so the print is complete and clean. Needs
  `pip install playwright && playwright install chromium`; skips with a hint if unavailable.

## Verification recipe

- Static: tag balance; grep output for external refs (must be none except optional `apple-touch-icon.png`); `node --check` on the `<script>`; assert `data:image/png;base64,` favicon present; TOC `<li>` count == h2 count and every `href="#x"` has a matching `id="x"`.
- Headless (playwright MCP, `file://`): `.layout/.sidebar ol li/header h1/footer` present; click `#copy-btn` → 3 `button[data-fmt]`; `document.querySelectorAll('.block-copy').length` ≈ details+callouts+tldr+standalone-pre+h2+h3; scroll → one `.sidebar a.active`; no failed network requests (no `/favicon.ico` 404).
