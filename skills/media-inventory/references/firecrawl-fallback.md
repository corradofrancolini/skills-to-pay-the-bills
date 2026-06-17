# Firecrawl fallback (JS-only / SPA sites)

Use Firecrawl **only** when the primary path (`curl`/sitemap + browser pass)
isn't enough: typically single-page apps where the static HTML is an empty shell
and media only appear after JS rendering, or when you want more robust page
discovery + extraction in one shot.

Firecrawl needs its own **`FIRECRAWL_API_KEY`**. If it isn't set:

```bash
echo 'export FIRECRAWL_API_KEY="fc-..."' >> ~/.env && source ~/.env
```

## Usage pattern

1. **Map the pages** (JS rendering included):
   ```bash
   firecrawl map https://example.com
   ```
2. **Scrape with rendered HTML** for each page, then feed that HTML to the same
   extractor used by the pipeline (`extract_assets`). For example, use
   `firecrawl scrape --formats html`, save the HTML to a folder, then:
   ```bash
   python3 scripts/inventory.py --url https://example.com --pages <pages from map> --out ./out
   ```
   (Alternatively, write the rendered HTML to files and adapt the script to read
   local HTML instead of re-fetching.)

## When Firecrawl is NOT needed

- Server-rendered sites (WordPress, most CMSs, classic marketing sites): the
  static HTML already contains the `<img>` tags. The `curl` pipeline is enough.
- Lazy-load / CSS background images: usually covered by the **browser pass** with
  Chrome DevTools MCP, without Firecrawl.
