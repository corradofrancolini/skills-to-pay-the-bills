---
name: media-inventory
description: >-
  Census the images and videos of a website — for every asset record its pixel
  dimensions, format/MIME, file weight (KB), and the page(s) it appears on, then
  output a CSV plus a Markdown table. Use this skill WHENEVER the user wants to
  inventory, audit, list, or census the media (images, photos, videos) of a site
  or page, asks how big / what format / how heavy the images or videos on a URL
  are, wants a media audit before a redesign or performance pass, or needs a
  spreadsheet of all assets on a site. Trigger even if the user doesn't say the
  word "inventory" — e.g. "how heavy are the images on X", "what format are the
  videos on Y", "list every photo on the site with its dimensions" — and
  regardless of the prompt's language. Do NOT trigger for compressing/optimizing/
  resizing images, for downloading a whole site for offline use, or for
  generating new images.
---

# Media inventory (images & videos of a website)

Given a website URL, produce an inventory of every image and video with its
**pixel dimensions, format/MIME, weight (KB), origin page(s)**, and whether it's
a responsive/derived variant. Output is an `inventory.csv` (for Excel/Sheets)
plus a readable `inventory.md` with a summary.

## When to use which mode

- **Single page** — user points at one URL: just probe that page.
- **Whole site** (`--site`) — user wants the whole site / all pages: discover
  pages from the sitemap (robots.txt → `sitemap*.xml`, nested indexes handled),
  with an internal-link crawl as fallback.
- **Specific pages** (`--pages` or `--pages-file`) — user names a few sections.

## Workflow

1. **Run the pipeline.** It is self-contained (stdlib only) and does the heavy
   lifting — discovery, extraction, probing, output:

   ```bash
   python3 scripts/inventory.py --url <URL> [--site | --pages URL... | --pages-file F] \
       --out <DIR> [--max-pages N] [--rpm 25] [--resume] [--source auto]
   ```

   It probes dimensions with `sips` (macOS native; `identify`/ImageMagick as
   fallback) for images, parses SVG as XML, and uses `ffprobe` for videos
   (read remotely — videos are **not** fully downloaded). Weight comes from the
   downloaded bytes (images) or `Content-Length` (videos).

2. **Browser verification pass (recommended for JS-heavy or lazy-loaded sites).**
   Static HTML parsing misses media injected by JS, some lazy-loaded images, and
   CSS `background-image`. On 3–5 representative pages, use Chrome DevTools MCP:
   - navigate + scroll to trigger lazy-loading,
   - `list_network_requests` filtered to Image/Media for real MIME + transfer size,
   - `evaluate_script` to read `naturalWidth/naturalHeight` (img), `videoWidth/
     videoHeight` (video), and `getComputedStyle(...).backgroundImage`.

   Add any assets the static pass missed to the CSV.

3. **Deliver** the CSV + Markdown summary, and point out anything notable
   (oversized images, missing dimensions, heavy videos).

## Output

`inventory.csv` — one row per asset:
`asset_url, type (image/video/svg), format, mime, width_px, height_px,
aspect_ratio, orientation, weight_kb, duration_s, is_variant, group,
alt, title, template_url, template_cms, source_pages, notes`

- `aspect_ratio` / `orientation` — derived from width×height (landscape/portrait/square).
- `is_variant` / `group` — `is_variant` flags CMS-generated sizes (`-300x200.jpg`); `group` is the source stem so originals and variants cluster.
- `alt` / `title` — text from the `<img>` tag (first non-empty across pages); useful for accessibility/SEO audits and as content to migrate.
- `template_url` — page type from the URL (first path segment after the locale).
- `template_cms` — page type from the WordPress `<body class>` (`single:product`, `category:…`, `tax:…`). On non-WordPress sites it degrades gracefully; `template_url` is the CMS-agnostic fallback.

`inventory.md` — summary: counts per format, **format × template matrices** (URL & CMS),
heaviest assets, images missing dimensions.

`formats_by_template.csv` / `formats_by_template_cms.csv` / `formats_by_page.csv` —
cross-tabs of **which formats are used in which template/page** (counts are
asset×page occurrences, i.e. usage, not unique assets).

WordPress and many CMSs generate derived sizes (`-300x200.jpg`, `-1024x683.jpg`).
These are flagged `is_variant=True` so you can separate originals from variants
while still listing every size that's actually served.

## Notes & edge cases

- **Be polite / avoid WAF blocks**: a global rate limiter caps requests per minute
  (`--rpm`, default 30 = one request every 2s, counting pages AND assets). Many
  WordPress sites run **Wordfence**, which returns **HTTP 503** ("Exceeded the
  maximum global requests per minute") and temporarily blocks your IP if you go too
  fast. The script backs off on 429/503 (respecting `Retry-After`). For a large
  site, keep `--rpm` low (20–30); if it's the client's own site, the cleanest path
  is to ask them to allowlist your IP in Wordfence, then raise `--rpm`. Asset
  probing uses a single GET per image (no extra HEAD) to halve requests; the
  `.cache/` makes re-runs cheap.
- **Adaptive backoff + clean abort**: on repeated 429/503 the limiter auto-slows
  (interval grows up to 15s) and, after ~8 consecutive blocks, **aborts cleanly in
  either phase** (page scan or asset probing) instead of grinding or recording empty
  rows.
- **Resume after a block/interruption**: phase 1 is checkpointed to
  `.manifest.json` in `--out`. Re-run with **`--resume`** to skip page scanning and
  reuse the cached downloads — only the not-yet-probed assets are fetched. Combine
  with **`--pages-file`** (one URL per line) for big explicit page lists. Outputs
  (CSV/MD) are written even on early abort, so a resumed run completes the rest.
- **JS-only sites (SPA)**: if the static pass finds almost nothing, the page is
  likely client-rendered — use the browser pass, or Firecrawl. See
  `references/firecrawl-fallback.md`.
- **Firecrawl**: optional fallback only. Never use a Gemini/Google backend;
  Firecrawl with its own API key is fine.
- **Dependencies**: `sips` ships with macOS; `ffprobe` via `brew install ffmpeg`;
  `identify` via ImageMagick (optional fallback). The script degrades gracefully
  and notes in the `notes` column when a probe tool is missing.
