# media-inventory

A Claude Code skill that **inventories the images and videos of a website**. For
every asset it records **pixel dimensions, format/MIME, file weight (KB), origin
page(s), `alt`/`title`, and template** (both URL- and CMS-derived), then writes a
CSV plus a readable Markdown summary with format×template matrices.

Built to survive real-world sites: a global rate limiter, adaptive backoff on
WAF/Wordfence rate-limits, clean abort, and **resume from a checkpoint**.

---

## How to use it (just ask Claude)

This is a **Claude Code skill** — you don't run anything yourself. Describe what you
want in natural language: the skill triggers automatically (no command to type), and
Claude runs the pipeline and hands you the CSV + summary. Example prompts:

- "Make an **inventory** of the images and videos on `https://www.example.com` — dimensions, format and weight, as a CSV."
- "**How heavy** are the images on example.com's homepage? Which ones are too big?"
- "**Inventory all the media** on the whole example.com site (every page) and tell me which formats are used in which type of page."
- "Inventory every image on `example.com/blog` and **flag the ones over 500 KB**."
- "**Audit the media** of this site before the redesign: list assets with width×height, format, and which template uses them."

You can steer it in plain language too:

- "go easy, the site is behind Wordfence" → lower request rate (`--rpm`)
- "just these 5 pages" / "the whole site" → explicit pages vs `--site`
- "resume where you left off" → resume from the checkpoint (`--resume`)

The CLI below is simply **what Claude runs under the hood** — handy if you ever want
to run it manually or in a script.

---

## What it produces

In the `--out` directory:

| File | Contents |
|------|----------|
| `inventory.csv` | One row per **unique asset**, all columns (see below). |
| `inventory.md` | Summary: counts per format, **format × template** matrices (URL & CMS), heaviest assets, images missing dimensions. |
| `formats_by_template.csv` / `_cms.csv` / `formats_by_page.csv` | Cross-tabs: which formats are used in which template / page (counts = asset×page occurrences). |
| `.cache/` | Downloaded asset bytes (so re-runs skip downloads). |
| `.manifest.json` | Phase-1 checkpoint (enables `--resume`). |

### CSV columns

`asset_url, type (image/video/svg), format, mime, width_px, height_px,
aspect_ratio, orientation, weight_kb, duration_s, is_variant, group, alt, title,
template_url, template_cms, source_pages, notes`

- **`aspect_ratio` / `orientation`** — derived from width×height (landscape/portrait/square).
- **`is_variant` / `group`** — `is_variant` flags CMS-generated sizes (`-1024x683.jpg`); `group` is the source stem so originals and their variants cluster.
- **`alt` / `title`** — from the `<img>` tag (accessibility/SEO; content to migrate).
- **`template_url`** — page type from the URL (first path segment after the locale: `products`, `recipes`, `home`…).
- **`template_cms`** — real page type from the WordPress `<body class>` (`single:product`, `category:…`, `tax:…`) — more precise than the URL heuristic.

---

## Requirements

- **Python 3** (standard library only — no `pip install`).
- **`sips`** — ships with macOS (image dimensions). Fallback: **ImageMagick** `identify`.
- **`ffprobe`** (`brew install ffmpeg`) — video dimensions/duration (read remotely; videos are not fully downloaded).

The script degrades gracefully and notes in the `notes` column when a tool is missing.

---

## Running the pipeline directly (CLI)

*(What the skill runs for you — also usable standalone.)*

```bash
# single page
python3 scripts/inventory.py --url https://example.com/ --out ./out

# whole site (sitemap discovery, link-crawl fallback), politely paced
python3 scripts/inventory.py --url https://example.com/ --site --rpm 25 --out ./out

# explicit pages from a file (one URL per line)
python3 scripts/inventory.py --url https://example.com/ --pages-file pages.txt --out ./out

# resume after a block/interruption (skips page scan, reuses .cache)
python3 scripts/inventory.py --url https://example.com/ --site --resume --out ./out
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--url URL` | (required) | Target page or site root. |
| `--site` | off | Crawl the whole site via `robots.txt` → `sitemap*.xml` (nested indexes handled), with an internal-link crawl fallback. |
| `--pages URL...` | — | Explicit list of pages to scan. |
| `--pages-file F` | — | File with one page URL per line (`#` comments allowed). |
| `--out DIR` | `media-inventory-out` | Output directory. |
| `--max-pages N` | 50 | Caps **auto-discovery** only (never an explicit `--pages`/`--pages-file` list). |
| `--rpm N` | 30 | Max requests/minute (global, pages **and** assets). Keep low (20–30) on WAF-protected sites. |
| `--throttle S` | 0 | Extra floor on seconds between requests (usually leave 0; `--rpm` governs). |
| `--resume` | off | Resume from `.manifest.json` in `--out`: skip page scanning, reuse cached downloads. |
| `--source MODE` | `scrape` | `scrape` (crawl pages) · `auto` (use the CMS media API if detected, else scrape) · `wp-api` / `shopify` (force that adapter). See below. |
| `--render` | off | Render each page in headless Chromium (Playwright) — captures JS/lazy/CSS-background media, DOM dimensions, and the served srcset variant. See below. |
| `--viewport WxH` | `1440x900` | Viewport for `--render` (also sets which srcset variant counts as served). |
| `--no-download` | off | Skip downloads (no pixel dimensions for images). |
| `--quiet` | off | Suppress progress logging. |

---

## CMS API mode (`--source`)

On a supported CMS, instead of crawling every page you can pull the **authoritative
media library** straight from the CMS API. This gives **reliable `upload_date`,
`alt` and dimensions**, uses **far fewer requests** (so it sidesteps WAF/Wordfence
rate-limits), and is much faster. Trade-off: it lists the *library*, not per-page
**usage** — so there's no `template`/`source_pages` data (use plain `scrape` for that).

```bash
python3 scripts/inventory.py --url https://example.com/ --source auto   --out ./out
python3 scripts/inventory.py --url https://example.com/ --source wp-api  --out ./out
```

Adapters (CMS-agnostic framework — add more by registering in `ADAPTERS`):

- **WordPress** — `/wp-json/wp/v2/media` (paginated): `source_url`, dimensions, `mime_type`, `alt_text`, `date`.
- **Shopify** — public `products.json`: product images with dimensions + `created_at`.
- **`auto`** detects the CMS from `<meta generator>` / headers and **falls back to scraping** if no adapter applies. Drupal/Ghost and others can be added the same way.

---

## Headless render mode (`--render`)

Static HTML parsing misses media injected by JS, some lazy-loaded images, and CSS
`background-image`. `--render` loads each page in **headless Chromium (Playwright)**,
auto-scrolls to trigger lazy-loading, and reads assets from the **live DOM**:

- catches **JS-injected / lazy / CSS-background** media the static parser can't see;
- reads **intrinsic dimensions from the DOM** (`naturalWidth/Height`) — so assets get
  sizes even with `--no-download`;
- records **`img.currentSrc`** — the **srcset variant actually served** at `--viewport`
  (e.g. `--viewport 375x812` to see what mobile gets).

```bash
python3 scripts/inventory.py --url https://example.com/ --site --render --out ./out
```

Optional dependency: `pip install playwright && playwright install chromium`. If it's
not installed, the skill prints how to install it and **falls back to static scraping**.
Render mode loads full pages (more requests than static), so keep `--rpm` polite.

---

## Resilience (WAF / rate-limit handling)

Many sites run **Wordfence** or similar, which returns **HTTP 503** ("Exceeded the
maximum global requests per minute") and temporarily blocks your IP if you go too
fast. This skill:

1. **Paces every request** (`--rpm`) — pages and assets share one global limiter.
2. **Backs off** on 429/503, respecting `Retry-After` (capped so a huge value can't freeze the run).
3. **Adaptively slows down** (interval grows up to 15s) as blocks accumulate.
4. **Aborts cleanly** after ~8 consecutive blocks — in *either* phase — instead of recording empty rows.
5. **Checkpoints phase 1** and writes partial outputs, so **`--resume`** finishes the rest without re-scanning pages or re-downloading cached assets.

On a site you control, the fastest path is to **allowlist your IP in Wordfence**
(or raise its rate limit) and then increase `--rpm`.

> Note: a dynamic ISP IP can change between runs, so IP-allowlisting may need
> re-doing; per-IP rotation does **not** beat a *global* (site-wide) per-minute cap.

---

## Limitations & complementary passes

- **JS-only / SPA sites**: static HTML parsing may miss media injected by JS,
  some lazy-loaded images, and CSS `background-image`. For key pages, do a browser
  verification pass (Chrome DevTools MCP: scroll to trigger lazy-load,
  `list_network_requests` for real MIME/size, `evaluate_script` for
  `naturalWidth/Height`), or use Firecrawl — see `references/firecrawl-fallback.md`.
- **True upload date / editorial metadata** live in the CMS, not in public assets.
- Responsive `srcset` "variant actually served" needs a real browser per breakpoint.

---

## Responsible use

This tool fetches publicly served pages and media. Use it responsibly:

- **Only on sites you own or are authorized to audit** (your own properties, or a
  client engagement with permission). It's a media audit tool, not a bulk scraper.
- **Respect `robots.txt`, Terms of Service, and rate limits.** The skill is polite
  by design (global `--rpm` limiter, backoff, clean abort) — keep it that way; don't
  crank `--rpm` to hammer a site.
- **Don't evade blocks.** If a site rate-limits you (e.g. Wordfence 503), slow down,
  resume later, or get the owner to allowlist you / raise the limit — don't rotate
  IPs or distribute requests to get around a site's own protections.
- **Respect copyright.** Downloaded bytes are cached locally only to measure
  dimensions/weight; the assets remain their owners' property.
- **Read-only.** The tool only issues GET/HEAD requests; it never modifies the site.

## Files

```
media-inventory/
├── SKILL.md                      # skill manifest + when-to-use + workflow
├── scripts/inventory.py          # the pipeline (stdlib only)
├── references/firecrawl-fallback.md
├── evals/evals.json              # test prompts
└── README.md                     # this file
```
