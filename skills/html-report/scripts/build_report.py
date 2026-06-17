#!/usr/bin/env python3
"""
html-report — render a content Markdown file into the fixed "house format"
self-contained HTML report (sidebar TOC, TL;DR, callouts, badges, collapsible
conversation evidence, 3-format copy/export, per-block copy icons, embedded favicon).

Usage:
  python3 build_report.py <content.md> [--out <path.html>] [--no-toc]
                          [--override-css <file>] [--override-js <file>]
                          [--favicon <png>]

Input contract (the stable seam — see references/authoring-guide.md):
  - YAML-ish front-matter, FLAT scalars only:
      title, date, author, subtitle, footer, lang, toc
  - Markdown body + pandoc fenced-div shortcodes (::: callout, ::: tldr),
    bracketed spans ([X]{.ok}, [Y]{.badge .badge-stable}), and raw HTML
    (<details> conversation evidence) passed through verbatim.

Deps: python3 stdlib + pandoc on PATH. No pip packages.
"""
import argparse, base64, json, mimetypes, os, re, shutil, subprocess, sys
from pathlib import Path


def inline_images_in_html(html: str, base_dir: Path, max_kb: int) -> str:
    """Embed <img src> as data: URIs (http/https or local files) for a fully
    self-contained, offline report. Images larger than max_kb are left linked."""
    import urllib.request
    limit = max_kb * 1024
    cache: dict[str, str | None] = {}

    def fetch(url: str):
        if url in cache:
            return cache[url]
        data = ctype = None
        try:
            if url.startswith(("http://", "https://")):
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 html-report"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    data, ctype = r.read(), r.headers.get_content_type()
            elif not url.startswith("data:"):
                p = Path(url) if os.path.isabs(url) else (base_dir / url)
                if p.exists():
                    data = p.read_bytes()
                    ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        except Exception:
            data = None
        rep = None
        if data is not None and len(data) <= limit:
            rep = f"data:{ctype or 'application/octet-stream'};base64,{base64.b64encode(data).decode()}"
        cache[url] = rep
        return rep

    def repl(m):
        whole, url = m.group(0), m.group(1)
        if url.startswith("data:"):
            return whole
        rep = fetch(url)
        return whole.replace(url, rep) if rep else whole

    return re.sub(r'<img\b[^>]*?\bsrc="([^"]+)"', repl, html)


def html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Render the built HTML to PDF with headless Chromium (Playwright). Expands
    all <details> and hides interactive chrome so the print is complete & clean."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.stderr.write("--pdf: Playwright not installed; skipping PDF.\n"
                         "  pip install playwright && playwright install chromium\n")
        return False
    hide = "@media print { #copy-btn, button[data-fmt], .block-copy { display:none !important; } }"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(Path(html_path).resolve().as_uri(), wait_until="networkidle")
            page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            page.add_style_tag(content=hide)
            page.pdf(path=str(pdf_path), format="A4", print_background=True,
                     margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
            browser.close()
        return True
    except Exception as e:
        sys.stderr.write(f"--pdf: failed to render PDF: {e}\n")
        return False


def require_pandoc() -> None:
    """Fail early with clear install guidance if pandoc isn't on PATH."""
    if shutil.which("pandoc") is None:
        sys.exit(
            "Error: 'pandoc' is required but was not found on PATH.\n"
            "Install it, then re-run:\n"
            "  macOS:          brew install pandoc\n"
            "  Debian/Ubuntu:  sudo apt-get install pandoc\n"
            "  Windows:        winget install --id JohnMacFarlane.Pandoc\n"
            "  Other / docs:   https://pandoc.org/installing.html"
        )

ASSETS = Path(__file__).resolve().parent.parent / "assets"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import shortcodes  # noqa: E402


def split_front_matter(text: str):
    """Return (front_matter_dict, body) for a leading ---\\n...\\n--- block."""
    fm = {}
    if text.startswith("---"):
        m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", text, re.S)
        if m:
            block, body = m.group(1), m.group(2)
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, _, val = line.partition(":")
                val = val.strip().strip('"').strip("'")
                fm[key.strip()] = val
            return fm, body
    return fm, text


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)            # strip inline tags
    text = re.sub(r"&[a-z]+;", "", text)            # strip entities
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "section"


def md_to_html(body_md: str) -> str:
    fmt = "markdown+fenced_divs+bracketed_spans+pipe_tables-auto_identifiers"
    proc = subprocess.run(
        ["pandoc", "-f", fmt, "-t", "html5", "--wrap=none"],
        input=body_md, text=True, capture_output=True,
    )
    if proc.returncode != 0:
        sys.exit(f"pandoc failed:\n{proc.stderr}")
    return proc.stdout


def assign_ids_and_toc(html: str, want_toc: bool):
    seen, toc = {}, []

    def repl(m):
        tag, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
        idm = re.search(r'\bid="([^"]+)"', attrs)
        if idm:
            hid, new_attrs = idm.group(1), attrs
        else:
            base = slugify(inner)
            n = seen.get(base, 0)
            hid = base if n == 0 else f"{base}-{n+1}"
            seen[base] = n + 1
            new_attrs = f'{attrs} id="{hid}"'
        if tag == "h2":
            toc.append((hid, re.sub(r"<[^>]+>", "", inner).strip()))
        return f"<{tag}{new_attrs}>{inner}</{tag}>"

    html = re.sub(r"<(h2|h3)((?:\s[^>]*)?)>(.*?)</\1>", repl, html, flags=re.S)
    if not want_toc:
        toc = []
    ol = "\n".join(f'        <li><a href="#{hid}">{text}</a></li>' for hid, text in toc)
    return html, ol


def data_uri(png_path: Path) -> str:
    b64 = base64.b64encode(png_path.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content")
    ap.add_argument("--out")
    ap.add_argument("--no-toc", action="store_true")
    ap.add_argument("--override-css")
    ap.add_argument("--override-js")
    ap.add_argument("--favicon")
    ap.add_argument("--inline-images", action="store_true",
                    help="Embed <img> sources as data: URIs (self-contained / offline).")
    ap.add_argument("--max-inline-kb", type=int, default=2048,
                    help="Skip inlining images larger than this (default 2048 KB).")
    ap.add_argument("--pdf", nargs="?", const="", default=None,
                    help="Also render a PDF (headless Chromium / Playwright). Optional output "
                         "path; defaults next to the HTML.")
    args = ap.parse_args()

    require_pandoc()

    src = Path(args.content)
    if not src.exists():
        sys.exit(f"content file not found: {src}")
    fm, body_md = split_front_matter(src.read_text())

    want_toc = not args.no_toc and str(fm.get("toc", "true")).lower() not in ("false", "no", "0")

    body = md_to_html(body_md)
    body = shortcodes.process(body)
    body, toc_ol = assign_ids_and_toc(body, want_toc)

    css = Path(args.override_css).read_text() if args.override_css else (ASSETS / "chrome.css").read_text()
    js  = Path(args.override_js).read_text()  if args.override_js  else (ASSETS / "report.js").read_text()
    favicon = data_uri(Path(args.favicon) if args.favicon else ASSETS / "favicon.png")

    title = fm.get("title", "Report")
    meta = " · ".join(x for x in (fm.get("date"), fm.get("author"), fm.get("subtitle")) if x)

    out_html = (ASSETS / "skeleton.html").read_text()
    for token, value in {
        "{{LANG}}": fm.get("lang", "en"),
        "{{TITLE}}": title,
        "{{FAVICON_DATAURI}}": favicon,
        "{{CSS}}": css,
        "{{H1}}": title,
        "{{META}}": meta,
        "{{TOC_OL}}": toc_ol,
        "{{BODY}}": body,
        "{{FOOTER}}": fm.get("footer", ""),
        "{{JS}}": js,
    }.items():
        out_html = out_html.replace(token, value)

    if args.inline_images:
        out_html = inline_images_in_html(out_html, src.parent, args.max_inline_kb)

    out_path = Path(args.out) if args.out else src.with_suffix(".html")
    out_path.write_text(out_html)

    # Machine-readable metadata sidecar (consumed by downstream index/hub generators).
    # Additive + project-agnostic: `client` is just a free string (default "misc").
    tags = [t.strip() for t in fm.get("tags", "").split(",") if t.strip()]
    meta = {
        "title": title,
        "date": fm.get("date", ""),
        "author": fm.get("author", ""),
        "subtitle": fm.get("subtitle", ""),
        "client": fm.get("client", "misc"),
        "tags": tags,
        "summary": fm.get("summary", ""),
        "html_filename": out_path.name,
    }
    out_path.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(out_path.resolve())

    if args.pdf is not None:
        pdf_path = Path(args.pdf) if args.pdf else out_path.with_suffix(".pdf")
        if html_to_pdf(out_path, pdf_path):
            print(pdf_path.resolve())


if __name__ == "__main__":
    main()
