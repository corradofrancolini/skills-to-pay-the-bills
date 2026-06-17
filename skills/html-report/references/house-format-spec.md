# House-format spec (frozen)

The "house format" is the fixed look of every report. It is **frozen**: a normal
`build_report.py` run cannot change it. Deviate ONLY when the user explicitly asks.

## Where the format lives (single source of truth)

| Asset | Role |
|-------|------|
| `assets/chrome.css` | All styling: layout grid, sticky sidebar TOC, typography, `.tldr`+`.label-*`, `.callout`+`.ct-title`, `.badge-*`, `.ok/.warn/.bad`, `.q-pill`, export CTA (`.copy-wrap/.copy-cta/.copy-menu/.copy-toast`), per-block `.copyable/.block-copy`, `@media print`. |
| `assets/report.js` | Export CTA (rich/markdown/plain via `htmlToMarkdown`/`buildRichHtml`/`buildPlain`/`copyFormat`); per-block copy injection (`COPY_SVG`, attaches `.block-copy` to `details`/`.callout`/`.tldr`/standalone `pre`/`h2`/`h3`); sidebar scroll-spy. |
| `assets/skeleton.html` | Body skeleton + `{{PLACEHOLDERS}}`. |
| `assets/favicon.png` | Default favicon (black circle), inlined as data-URI. |

These four files ARE the format. They were extracted verbatim from the reference report
`~/Projects/EFG/reports/2026-05-28-models-migration-tier1.html`.

## Deviation mechanism (the only one)

`build_report.py` has no styling parameters. Content flows only into `{{BODY}}`, `{{TOC_OL}}`,
`{{META}}`, `{{TITLE}}`, `{{H1}}`, `{{FOOTER}}`. The sole deviation path:

- `--override-css <file>` / `--override-js <file>` / `--favicon <png>`.

Rules when a deviation IS requested:
1. Never edit the default asset files in place.
2. Copy the asset to a scratch file, edit the copy, pass it via `--override-*`.
3. Keep the deviation scoped to that one report unless told to make it the new default.

If asked to change the format *permanently*, that's a deliberate edit of the asset files —
treat it as a format version bump, not an ad-hoc tweak.

## Metadata sidecar

`build_report.py` also writes a `<name>.meta.json` next to the `.html` (title, date, author, subtitle, `client`, `tags`, `summary`, `html_filename`). It is the machine-readable source consumed by downstream index/hub generators; it does **not** affect the self-contained HTML and is not part of the frozen chrome.

## Self-containment invariant

Output is a single HTML file. CSS, JS and favicon are inlined. The only acceptable external
reference is an optional `apple-touch-icon.png` (cosmetic, 404-safe). The verification step greps
for any other external `src=`/`href="http"` (outside in-content links) and must find none.

## Runtime behaviors that are part of the format

- Per-block copy icons are **injected by JS at runtime** — never authored in the body.
- Sidebar TOC is **auto-generated** from `<h2>` headings; ids are auto-assigned.
- The export CTA copies the whole report in 3 formats; per-block copies copy that block.
- `<pre>` nested inside `<details>` does NOT get its own copy icon (only standalone `pre` do).
