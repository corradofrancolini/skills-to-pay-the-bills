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
import argparse, base64, json, re, shutil, subprocess, sys
from pathlib import Path


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


if __name__ == "__main__":
    main()
