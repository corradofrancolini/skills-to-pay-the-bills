#!/usr/bin/env python3
"""media-inventory: census images and videos of a website.

For each image/video found on the target page(s) or whole site, record:
  - asset URL and the page(s) it appears on
  - format / MIME
  - pixel dimensions (width x height)
  - weight in KB
  - duration (videos)
  - whether it is a responsive/derived variant (e.g. WordPress -300x200.jpg)

Stdlib-only (no pip installs). Pixel probing relies on external tools that are
standard on macOS / common elsewhere:
  - images:  `sips` (macOS native)  with fallback to ImageMagick `identify`
  - videos:  `ffprobe` (reads remote URLs, so videos are NOT fully downloaded)
  - SVG:     parsed as XML (width/height/viewBox)

Usage:
  inventory.py --url URL [--site | --pages URL ... | --pages-file F] [--out DIR]
               [--max-pages N] [--rpm N] [--resume] [--no-download] [--quiet]

Examples:
  # single page
  inventory.py --url https://example.com/

  # whole site via sitemap (fallback: internal link crawl), politely paced
  inventory.py --url https://example.com/ --site --rpm 25 --out ./out
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "avif", "bmp", "tiff", "tif", "ico", "svg"}
VIDEO_EXT = {"mp4", "webm", "mov", "m4v", "ogv", "avi", "mkv"}

VARIANT_RE = re.compile(r"-\d+x\d+(?=\.\w+$)")
SRCSET_RE = re.compile(r"\s*([^\s,]+)(?:\s+[^,]+)?\s*(?:,|$)")
BG_URL_RE = re.compile(r"url\((['\"]?)(.*?)\1\)", re.IGNORECASE)


def log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
_RATE = {"interval": 0.0, "last": 0.0}  # global request pacing (seconds between any HTTP call)
_BLOCK = {"streak": 0, "max_interval": 15.0}  # consecutive 429/503 across ALL requests
ABORT_AFTER_BLOCKS = 8  # give up (cleanly) after this many consecutive blocks


def blocked_too_much() -> bool:
    return _BLOCK["streak"] >= ABORT_AFTER_BLOCKS


def _note_block():
    """Record a rate-limit hit and adaptively slow down (auto-backoff)."""
    _BLOCK["streak"] += 1
    if _RATE["interval"] > 0:
        _RATE["interval"] = min(_RATE["interval"] * 1.5, _BLOCK["max_interval"])


def _throttle_global():
    """Enforce a global minimum interval between ANY outgoing request (pages and
    assets alike). This is what a per-minute limiter like Wordfence measures."""
    if _RATE["interval"] <= 0:
        return
    now = time.monotonic()
    wait = _RATE["interval"] - (now - _RATE["last"])
    if wait > 0:
        time.sleep(wait)
    _RATE["last"] = time.monotonic()


def http_get(url: str, timeout: int = 25, retries: int = 3):
    """Return (status, headers_dict, body_bytes). status is the HTTP code (or
    None on network error); body is b'' on failure. Backs off on 429/503 and
    respects Retry-After so we don't hammer a rate-limiting server."""
    last_err = None
    status = None
    for attempt in range(retries + 1):
        _throttle_global()
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
                _BLOCK["streak"] = 0  # a success clears the block streak
                return resp.status, headers, body
        except HTTPError as e:
            status = e.code
            last_err = e
            if e.code in (429, 503):  # rate-limited / unavailable -> back off hard
                retry_after = e.headers.get("Retry-After") if e.headers else None
                wait = int(retry_after) if (retry_after or "").isdigit() else 3 * (2 ** attempt)
                wait = min(wait, 30)  # cap: never freeze on a huge Retry-After
                time.sleep(wait)
            else:
                time.sleep(0.6 * (attempt + 1))
        except (URLError, TimeoutError, OSError) as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    if status in (429, 503):  # exhausted retries on a rate-limit -> count + adaptive slowdown
        _note_block()
    return status, {"_error": str(last_err)}, b""


def http_head(url: str, timeout: int = 20):
    """HEAD request; returns headers dict (lowercased) or {}."""
    _throttle_global()
    try:
        req = Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urlopen(req, timeout=timeout) as resp:
            return {k.lower(): v for k, v in resp.headers.items()}
    except (HTTPError, URLError, TimeoutError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Page discovery
# --------------------------------------------------------------------------- #
def discover_via_sitemap(base_url: str, quiet: bool) -> list[str]:
    """Find page URLs from robots.txt -> sitemap(s). Handles nested indexes."""
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []

    # robots.txt
    _, _, body = http_get(urljoin(root, "/robots.txt"))
    for line in body.decode("utf-8", "ignore").splitlines():
        if line.lower().startswith("sitemap:"):
            candidates.append(line.split(":", 1)[1].strip())
    # common defaults
    candidates += [urljoin(root, "/sitemap_index.xml"), urljoin(root, "/sitemap.xml")]

    pages: list[str] = []
    seen_sitemaps: set[str] = set()
    queue = list(dict.fromkeys(candidates))
    while queue:
        sm = queue.pop(0)
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        status, headers, body = http_get(sm)
        if not body or (status and status >= 400):
            continue
        # ignore HTML error pages served for missing sitemaps
        ctype = headers.get("content-type", "")
        if "html" in ctype and b"<urlset" not in body and b"<sitemapindex" not in body:
            continue
        try:
            root_el = ET.fromstring(body)
        except ET.ParseError:
            continue
        tag = root_el.tag.lower()
        if tag.endswith("sitemapindex"):
            for loc in root_el.iter():
                if loc.tag.lower().endswith("loc") and loc.text:
                    queue.append(loc.text.strip())
        else:  # urlset — take page <loc>, but NOT <image:loc> (image namespace)
            for url_el in root_el.iter():
                t = url_el.tag.lower()
                if t.endswith("loc") and "image" not in t and url_el.text:
                    pages.append(url_el.text.strip())
        log(f"  sitemap {sm}: total pages so far {len(set(pages))}", quiet)

    # keep only same-host URLs
    host = parsed.netloc
    out = [u for u in dict.fromkeys(pages) if urlparse(u).netloc == host]
    return out


def discover_via_crawl(base_url: str, max_pages: int, throttle: float, quiet: bool) -> list[str]:
    """Fallback: BFS crawl of internal links, same host."""
    host = urlparse(base_url).netloc
    seen = {urldefrag(base_url)[0]}
    order = [urldefrag(base_url)[0]]
    queue = [urldefrag(base_url)[0]]
    while queue and len(order) < max_pages:
        page = queue.pop(0)
        status, headers, body = http_get(page)
        if not body or "html" not in headers.get("content-type", ""):
            continue
        for m in re.finditer(r'href=["\']([^"\'#]+)', body.decode("utf-8", "ignore")):
            link = urldefrag(urljoin(page, m.group(1)))[0]
            if urlparse(link).netloc == host and link not in seen:
                seen.add(link)
                order.append(link)
                queue.append(link)
        time.sleep(throttle)
    return order[:max_pages]


# --------------------------------------------------------------------------- #
# Asset extraction from HTML
# --------------------------------------------------------------------------- #
class AssetExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.assets: list[tuple[str, str]] = []  # (abs_url, kind_hint)
        self.meta: dict[str, dict] = {}          # abs_url -> {alt, title}
        self.body_class: str = ""                # <body class> of the page

    def _add(self, raw, kind, meta=None):
        if not raw:
            return
        raw = raw.strip()
        if not raw or raw.startswith("data:"):
            return
        url = urljoin(self.base, raw)
        self.assets.append((url, kind))
        if meta:
            cur = self.meta.setdefault(url, {})
            for k, v in meta.items():
                if v and not cur.get(k):
                    cur[k] = v

    def _add_srcset(self, srcset, kind, meta=None):
        if not srcset:
            return
        for m in SRCSET_RE.finditer(srcset):
            self._add(m.group(1), kind, meta)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "body" and not self.body_class:
            self.body_class = (a.get("class") or "").strip()
        if tag == "img":
            m = {"alt": (a.get("alt") or "").strip(), "title": (a.get("title") or "").strip()}
            self._add(a.get("src"), "image", m)
            for k in ("data-src", "data-lazy-src", "data-original"):
                self._add(a.get(k), "image", m)
            self._add_srcset(a.get("srcset"), "image", m)
            self._add_srcset(a.get("data-srcset"), "image", m)
        elif tag == "source":
            # inside <picture> (image) or <video>/<audio> (media)
            self._add_srcset(a.get("srcset"), "image")
            self._add(a.get("src"), "media")
        elif tag == "video":
            self._add(a.get("src"), "video")
            self._add(a.get("poster"), "image")
        elif tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            if prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
                self._add(a.get("content"), "image")
        elif tag == "link":
            if (a.get("rel") or "").lower() in ("image_src", "apple-touch-icon", "icon"):
                self._add(a.get("href"), "image")
        # inline background-image on any element
        style = a.get("style")
        if style and "url(" in style:
            for m in BG_URL_RE.finditer(style):
                self._add(m.group(2), "image")


def extract_assets(page_url: str, html: bytes):
    parser = AssetExtractor(page_url)
    try:
        parser.feed(html.decode("utf-8", "ignore"))
    except Exception:
        pass
    # dedup within page, keep first kind hint
    seen = {}
    for url, kind in parser.assets:
        url = urldefrag(url)[0]
        if url not in seen:
            seen[url] = kind
    meta = {urldefrag(u)[0]: m for u, m in parser.meta.items()}
    return list(seen.items()), meta, parser.body_class


# --------------------------------------------------------------------------- #
# Asset probing
# --------------------------------------------------------------------------- #
def ext_of(url: str) -> str:
    path = urlparse(url).path
    return path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""


def classify(url: str, mime: str, hint: str) -> str:
    ext = ext_of(url)
    if ext == "svg" or mime == "image/svg+xml":
        return "svg"
    if ext in VIDEO_EXT or mime.startswith("video/"):
        return "video"
    if ext in IMAGE_EXT or mime.startswith("image/"):
        return "image"
    if hint in ("video", "image", "svg"):
        return hint
    if hint == "media":
        return "video"
    return "other"


def template_of(url: str) -> str:
    """Heuristic page-template label from the URL path: the first path segment
    after an optional 2-letter locale (e.g. /en/recipes/... -> 'recipes',
    /en/ -> 'home'). CMS-agnostic; works well for common path conventions."""
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    if parts and len(parts[0]) == 2:  # drop locale like 'it', 'en'
        parts = parts[1:]
    return parts[0] if parts else "home"


def template_cms_label(class_str: str) -> str:
    """Derive the page-type from the WordPress <body class>. More precise than the
    URL heuristic: distinguishes single vs archive, custom post types, page
    templates, taxonomies. On non-WordPress sites it degrades to the first class
    (the URL template always remains as a CMS-agnostic fallback)."""
    classes = (class_str or "").split()
    cset = set(classes)
    for c in classes:
        if c.startswith("page-template-") and c != "page-template-default":
            return "template:" + c[len("page-template-"):]
    if "home" in cset or "front-page" in cset:
        return "home"
    for c in classes:
        if c.startswith("single-") and not c.startswith("single-format"):
            return "single:" + c[len("single-"):]
    for c in classes:
        if c.startswith("post-type-archive-"):
            return "archive:" + c[len("post-type-archive-"):]
    for c in classes:
        if c.startswith("category-"):
            return "category:" + c[len("category-"):]
    for c in classes:
        if c.startswith("tax-"):
            return "tax:" + c[len("tax-"):]
    for key in ("archive", "blog", "search", "page"):
        if key in cset:
            return key
    return classes[0] if classes else "?"


def format_breakdown(records, page_cms=None):
    """Cross-tab of format usage by URL-template, by CMS-template, and by page.
    Returns (per_template, per_template_cms, per_page, sorted_formats)."""
    page_cms = page_cms or {}
    per_template: dict[str, dict[str, int]] = {}
    per_template_cms: dict[str, dict[str, int]] = {}
    per_page: dict[str, dict[str, int]] = {}
    formats: set[str] = set()
    for r in records:
        fmt = (r.get("format") or "?").lower()
        formats.add(fmt)
        pages = r.get("source_pages") or []
        if isinstance(pages, str):
            pages = [p.strip() for p in pages.split("|") if p.strip()]
        for p in pages:
            per_page.setdefault(p, {})[fmt] = per_page.setdefault(p, {}).get(fmt, 0) + 1
            t = template_of(p)
            per_template.setdefault(t, {})[fmt] = per_template.setdefault(t, {}).get(fmt, 0) + 1
            tc = page_cms.get(p) or "?"
            per_template_cms.setdefault(tc, {})[fmt] = per_template_cms.setdefault(tc, {}).get(fmt, 0) + 1
    return per_template, per_template_cms, per_page, sorted(formats)


def write_breakdown_csv(path, per_group, formats, key_name):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([key_name] + formats + ["total"])
        for g, counts in sorted(per_group.items(), key=lambda kv: -sum(kv[1].values())):
            w.writerow([g] + [counts.get(fmt, 0) for fmt in formats] + [sum(counts.values())])


def run(cmd: list[str], timeout: int = 60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def sips_dims(path: str):
    res = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "format", path])
    if not res or res.returncode != 0:
        return None
    w = h = None
    fmt = ""
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("pixelWidth:"):
            w = int(line.split(":")[1])
        elif line.startswith("pixelHeight:"):
            h = int(line.split(":")[1])
        elif line.startswith("format:"):
            fmt = line.split(":")[1].strip()
    if w and h:
        return w, h, fmt
    return None


def identify_dims(path: str):
    res = run(["identify", "-format", "%w %h %m", path])
    if not res or res.returncode != 0:
        return None
    parts = res.stdout.strip().split()
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1]), (parts[2] if len(parts) > 2 else "")
    return None


def image_dims(data: bytes):
    """Pure-Python intrinsic dimensions by parsing file headers. No external tools,
    cross-platform. Handles PNG/JPEG/GIF/BMP/WebP/AVIF-HEIF/ICO. Returns (w, h, fmt)
    or None (then sips/identify can still be tried as a fallback)."""
    if not data or len(data) < 24:
        return None
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"), "png"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return int.from_bytes(data[6:8], "little"), int.from_bytes(data[8:10], "little"), "gif"
        if data[:2] == b"\xff\xd8":  # JPEG: scan for a SOF marker
            i, n = 2, len(data)
            while i + 9 < n:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker == 0xD8 or marker == 0xD9 or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = int.from_bytes(data[i + 2:i + 4], "big")
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    return (int.from_bytes(data[i + 7:i + 9], "big"),
                            int.from_bytes(data[i + 5:i + 7], "big"), "jpeg")
                i += 2 + seg
            return None
        if data[:2] == b"BM":
            return (int.from_bytes(data[18:22], "little"),
                    abs(int.from_bytes(data[22:26], "little", signed=True)), "bmp")
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
                return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                        int.from_bytes(data[28:30], "little") & 0x3FFF, "webp")
            if chunk == b"VP8L" and data[20] == 0x2F:
                b = int.from_bytes(data[21:25], "little")
                return ((b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1, "webp")
            if chunk == b"VP8X":
                return (int.from_bytes(data[24:27], "little") + 1,
                        int.from_bytes(data[27:30], "little") + 1, "webp")
            return None
        if data[4:8] == b"ftyp":  # ISO-BMFF: AVIF / HEIF — read the 'ispe' box
            j = data.find(b"ispe")
            if j != -1 and j + 16 <= len(data):
                w = int.from_bytes(data[j + 8:j + 12], "big")
                h = int.from_bytes(data[j + 12:j + 16], "big")
                if w and h:
                    fmt = "avif" if b"avif" in data[:32] else "heif"
                    return w, h, fmt
            return None
        if data[:4] in (b"\x00\x00\x01\x00", b"\x00\x00\x02\x00"):  # ICO/CUR
            return (data[6] or 256), (data[7] or 256), "ico"
    except Exception:
        return None
    return None


def svg_dims(body: bytes):
    try:
        el = ET.fromstring(body)
    except ET.ParseError:
        return None
    def num(v):
        m = re.match(r"[\d.]+", v or "")
        return float(m.group(0)) if m else None
    w = num(el.get("width"))
    h = num(el.get("height"))
    if (w is None or h is None) and el.get("viewBox"):
        vb = el.get("viewBox").replace(",", " ").split()
        if len(vb) == 4:
            w = w or float(vb[2])
            h = h or float(vb[3])
    if w and h:
        return int(round(w)), int(round(h)), "SVG"
    return None


def ffprobe_video(url: str):
    res = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name",
        "-show_entries", "format=duration",
        "-of", "json", url,
    ], timeout=90)
    if not res or res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    w = stream.get("width")
    h = stream.get("height")
    dur = fmt.get("duration")
    return {
        "width": w, "height": h,
        "codec": stream.get("codec_name", ""),
        "duration": round(float(dur), 2) if dur else None,
    }


def cache_path(out_dir: str, url: str) -> str:
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    ext = ext_of(url) or "bin"
    return os.path.join(out_dir, ".cache", f"{h}.{ext}")


def probe_asset(url: str, kind_hint: str, out_dir: str, download: bool, quiet: bool) -> dict:
    rec = {
        "asset_url": url, "type": "", "format": ext_of(url), "mime": "",
        "width_px": "", "height_px": "", "weight_kb": "", "duration_s": "",
        "is_variant": bool(VARIANT_RE.search(urlparse(url).path)), "notes": "",
    }
    prelim = classify(url, "", kind_hint)  # classify by extension/hint, no network

    if prelim == "video":
        head = http_head(url)
        rec["mime"] = (head.get("content-type", "").split(";")[0]).strip()
        rec["type"] = classify(url, rec["mime"], kind_hint)
        clen = head.get("content-length")
        if clen:
            rec["weight_kb"] = round(int(clen) / 1024, 1)
        info = ffprobe_video(url)
        if info:
            rec["width_px"] = info["width"] or ""
            rec["height_px"] = info["height"] or ""
            rec["duration_s"] = info["duration"] or ""
            if info["codec"]:
                rec["format"] = rec["format"] or info["codec"]
        else:
            rec["notes"] = "ffprobe unavailable or stream unreadable"
        return rec

    if not download:
        head = http_head(url)
        rec["mime"] = (head.get("content-type", "").split(";")[0]).strip()
        rec["type"] = classify(url, rec["mime"], kind_hint)
        clen = head.get("content-length")
        if clen:
            rec["weight_kb"] = round(int(clen) / 1024, 1)
        rec["notes"] = "no-download: pixel dimensions not detected"
        return rec

    # images / svg / other -> single GET (no HEAD): gives weight + dimensions + mime
    cpath = cache_path(out_dir, url)
    body = b""
    if os.path.exists(cpath) and os.path.getsize(cpath) > 0:
        with open(cpath, "rb") as f:
            body = f.read()
    else:
        status, headers, body = http_get(url)
        if not body:
            rec["type"] = prelim
            rec["notes"] = f"download failed ({status or headers.get('_error', '?')})"
            return rec
        rec["mime"] = (headers.get("content-type", "").split(";")[0]).strip()
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        with open(cpath, "wb") as f:
            f.write(body)

    rec["weight_kb"] = round(len(body) / 1024, 1)
    rec["type"] = classify(url, rec["mime"], kind_hint)

    dims = None
    if rec["type"] == "svg" or ext_of(url) == "svg":
        dims = svg_dims(body)
        rec["type"] = "svg"
    else:
        # pure-Python header parse first (cross-platform, no tools); sips/identify fallback
        dims = image_dims(body) or sips_dims(cpath) or identify_dims(cpath)
    if dims:
        rec["width_px"], rec["height_px"] = dims[0], dims[1]
        if dims[2]:
            rec["format"] = rec["format"] or dims[2].lower()
    elif not rec["notes"]:
        rec["notes"] = "pixel dimensions not detected"
    return rec


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
CSV_FIELDS = ["asset_url", "type", "format", "mime", "width_px", "height_px",
              "aspect_ratio", "orientation", "weight_kb", "duration_s",
              "is_variant", "group", "alt", "title", "upload_date",
              "template_url", "template_cms", "source_pages", "notes"]


def derive_fields(rec: dict) -> dict:
    """Fill aspect_ratio, orientation and group from width/height + asset_url.
    Shared by the scraping path and the CMS-API adapters."""
    try:
        w = float(rec.get("width_px") or 0)
        h = float(rec.get("height_px") or 0)
    except (TypeError, ValueError):
        w = h = 0
    if w and h:
        ratio = w / h
        rec["aspect_ratio"] = round(ratio, 2)
        rec["orientation"] = ("square" if 0.95 <= ratio <= 1.05
                              else "landscape" if ratio > 1 else "portrait")
    else:
        rec["aspect_ratio"] = rec.get("aspect_ratio", "") or ""
        rec["orientation"] = rec.get("orientation", "") or ""
    fname = urlparse(rec.get("asset_url", "")).path.rsplit("/", 1)[-1]
    rec["group"] = re.sub(r"\.\w+$", "", VARIANT_RE.sub("", fname))
    return rec


def write_csv(path: str, records: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in records:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            if isinstance(row.get("source_pages"), (list, set)):
                row["source_pages"] = " | ".join(sorted(row["source_pages"]))
            w.writerow(row)


def write_md(path: str, records: list[dict], target: str, n_pages: int, page_cms=None):
    by_format: dict[str, int] = {}
    total_kb = 0.0
    n_img = n_vid = n_novar = 0
    for r in records:
        fmt = (r.get("format") or "?").lower()
        by_format[fmt] = by_format.get(fmt, 0) + 1
        try:
            total_kb += float(r.get("weight_kb") or 0)
        except (TypeError, ValueError):
            pass
        if r.get("type") == "video":
            n_vid += 1
        elif r.get("type") in ("image", "svg"):
            n_img += 1
        if not r.get("is_variant"):
            n_novar += 1

    per_template, per_template_cms, _per_page, fmts = format_breakdown(records, page_cms)
    heaviest = sorted(records, key=lambda r: float(r.get("weight_kb") or 0), reverse=True)[:10]
    missing = [r for r in records if not r.get("width_px") and r.get("type") in ("image", "svg")]

    lines = []
    lines.append(f"# Media inventory — {target}\n")
    if n_pages:
        lines.append(f"- Pages analyzed: **{n_pages}**")
    else:
        lines.append("- Source: **CMS media library (API)**")
    lines.append(f"- Total assets (unique): **{len(records)}** "
                 f"({n_img} images/SVG, {n_vid} videos, {n_novar} non-variant)")
    lines.append(f"- Total asset weight: **{total_kb/1024:.1f} MB**")
    lines.append("\n## Count by format\n")
    lines.append("| Format | Assets |")
    lines.append("|---|---|")
    for fmt, n in sorted(by_format.items(), key=lambda x: -x[1]):
        lines.append(f"| {fmt} | {n} |")

    def matrix(title, per_group, label):
        lines.append(f"\n## {title}\n")
        lines.append(f"| {label} | " + " | ".join(fmts) + " | Total |")
        lines.append("|" + "---|" * (len(fmts) + 2))
        for g, counts in sorted(per_group.items(), key=lambda kv: -sum(kv[1].values())):
            row = " | ".join(str(counts.get(f, 0)) for f in fmts)
            lines.append(f"| {g} | {row} | {sum(counts.values())} |")

    if per_template:
        matrix("Formats by template (from URL)", per_template, "Template URL")
    if per_template_cms:
        matrix("Formats by template (from CMS / body class)", per_template_cms, "Template CMS")

    lines.append("\n## Top 10 heaviest assets\n")
    lines.append("| Weight (KB) | Type | Dimensions | URL |")
    lines.append("|---|---|---|---|")
    for r in heaviest:
        dim = f"{r.get('width_px','?')}×{r.get('height_px','?')}"
        lines.append(f"| {r.get('weight_kb','')} | {r.get('type','')} | {dim} | {r['asset_url']} |")

    if missing:
        lines.append(f"\n## Images without detected dimensions ({len(missing)})\n")
        for r in missing[:30]:
            lines.append(f"- {r['asset_url']} — {r.get('notes','')}")

    lines.append("\n## All assets\n")
    lines.append("| Type | Format | Dim (px) | Weight (KB) | Duration | Var | URL |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in sorted(records, key=lambda r: (r.get("type", ""), -float(r.get("weight_kb") or 0))):
        dim = f"{r.get('width_px','')}×{r.get('height_px','')}".strip("×")
        var = "✓" if r.get("is_variant") else ""
        lines.append(f"| {r.get('type','')} | {r.get('format','')} | {dim} | "
                     f"{r.get('weight_kb','')} | {r.get('duration_s','')} | {var} | {r['asset_url']} |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# CMS API adapters
# Pull the authoritative media library from a CMS API instead of scraping:
# reliable upload_date / alt / dimensions, far fewer requests (avoids WAF blocks).
# Trade-off: gives the library, not per-page usage (no template/source-page data).
# Each adapter returns a list of records in the CSV_FIELDS shape; the framework
# is CMS-agnostic — add an adapter and register it in ADAPTERS.
# --------------------------------------------------------------------------- #
def _site_root(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def detect_cms(base_url: str, quiet: bool = False):
    """Best-effort CMS detection from <meta generator>, headers, and telltales."""
    status, headers, body = http_get(base_url)
    html = body.decode("utf-8", "ignore") if body else ""
    gen = ""
    m = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if m:
        gen = m.group(1).lower()
    blob = " ".join([gen, (headers.get("x-powered-by", "") or "").lower(), html[:8000].lower()])
    if "wordpress" in gen or "/wp-json/" in html or "/wp-content/" in html:
        return "wordpress"
    if "shopify" in blob or "cdn.shopify.com" in html:
        return "shopify"
    if "drupal" in gen or "drupal-settings-json" in html:
        return "drupal"
    if "ghost" in gen:
        return "ghost"
    return None


def _api_record(url: str, mime: str = "") -> dict:
    return {"asset_url": url, "type": classify(url, mime, ""), "format": ext_of(url),
            "mime": mime, "width_px": "", "height_px": "", "weight_kb": "", "duration_s": "",
            "is_variant": bool(VARIANT_RE.search(urlparse(url).path)), "alt": "", "title": "",
            "upload_date": "", "source_pages": "", "template_url": "", "template_cms": "", "notes": ""}


def wp_media_records(base_url: str, quiet: bool) -> list[dict]:
    """WordPress REST API: /wp-json/wp/v2/media (paginated)."""
    root = _site_root(base_url)
    recs, page = [], 1
    while True:
        api = urljoin(root, f"/wp-json/wp/v2/media?per_page=100&page={page}"
                            "&_fields=source_url,mime_type,media_details,alt_text,title,date")
        status, headers, body = http_get(api)
        if not body or (status and status >= 400):
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        if not isinstance(data, list) or not data:
            break
        for it in data:
            url = it.get("source_url") or ""
            if not url:
                continue
            rec = _api_record(url, (it.get("mime_type") or ""))
            md = it.get("media_details") or {}
            if md.get("width"):
                rec["width_px"] = md["width"]
            if md.get("height"):
                rec["height_px"] = md["height"]
            rec["alt"] = (it.get("alt_text") or "").strip()
            rec["title"] = re.sub("<[^>]+>", "", ((it.get("title") or {}).get("rendered") or "")).strip()
            rec["upload_date"] = (it.get("date") or "")[:10]
            rec["notes"] = "from WP REST API"
            recs.append(derive_fields(rec))
        total = int(headers.get("x-wp-totalpages", "0") or 0)
        log(f"  WP media: page {page}/{total or '?'} ({len(recs)} items)", quiet)
        if not total or page >= total:
            break
        page += 1
    return recs


def shopify_records(base_url: str, quiet: bool) -> list[dict]:
    """Shopify public products.json → product images (with dimensions + created_at)."""
    root = _site_root(base_url)
    recs, page, seen = [], 1, set()
    while True:
        api = urljoin(root, f"/products.json?limit=250&page={page}")
        status, headers, body = http_get(api)
        if not body or (status and status >= 400):
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        products = data.get("products") if isinstance(data, dict) else None
        if not products:
            break
        for p in products:
            ptitle = p.get("title") or ""
            for img in (p.get("images") or []):
                url = (img.get("src") or "").split("?")[0]
                if not url or url in seen:
                    continue
                seen.add(url)
                rec = _api_record(url)
                if img.get("width"):
                    rec["width_px"] = img["width"]
                if img.get("height"):
                    rec["height_px"] = img["height"]
                rec["alt"] = (img.get("alt") or ptitle or "").strip()
                rec["upload_date"] = (img.get("created_at") or "")[:10]
                rec["notes"] = "from Shopify products.json"
                recs.append(derive_fields(rec))
        log(f"  Shopify: page {page} ({len(recs)} images)", quiet)
        if len(products) < 250:
            break
        page += 1
    return recs


def payload_records(base_url: str, quiet: bool, collection: str = "media") -> list[dict]:
    """Payload CMS REST API: /api/<upload-collection> (default 'media'), paginated.
    Gives url, dimensions, mimeType, alt, createdAt and filesize (→ weight, for free)."""
    root = _site_root(base_url)
    recs, page = [], 1
    while True:
        api = urljoin(root, f"/api/{collection}?limit=100&page={page}&depth=0")
        status, headers, body = http_get(api)
        if not body or (status and status >= 400):
            break
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            break
        docs = data.get("docs") if isinstance(data, dict) else None
        if not docs:
            break
        for d in docs:
            raw = d.get("url") or (f"/{collection}/{d['filename']}" if d.get("filename") else "")
            if not raw:
                continue
            rec = _api_record(urljoin(root, raw), (d.get("mimeType") or ""))
            if d.get("width"):
                rec["width_px"] = d["width"]
            if d.get("height"):
                rec["height_px"] = d["height"]
            if d.get("filesize"):
                rec["weight_kb"] = round(int(d["filesize"]) / 1024, 1)
            rec["alt"] = (d.get("alt") or "").strip() if isinstance(d.get("alt"), str) else ""
            rec["upload_date"] = (d.get("createdAt") or "")[:10]
            rec["notes"] = "from Payload REST API"
            recs.append(derive_fields(rec))
        log(f"  Payload media: page {page}/{data.get('totalPages', '?')} ({len(recs)} items)", quiet)
        if not data.get("hasNextPage"):
            break
        page += 1
    return recs


ADAPTERS = {"wordpress": wp_media_records, "shopify": shopify_records, "payload": payload_records}


def inventory_via_api(base_url: str, source: str, quiet: bool):
    """source: a CMS name in ADAPTERS, or 'auto' to detect. Returns records or None."""
    cms = source if source in ADAPTERS else detect_cms(base_url, quiet)
    if cms not in ADAPTERS:
        log(f"API mode: no supported CMS adapter (detected: {cms or 'unknown'}). "
            "Supported: " + ", ".join(ADAPTERS), quiet)
        return None
    log(f"API mode: using the '{cms}' adapter (CMS media library).", quiet)
    return ADAPTERS[cms](base_url, quiet) or None


# --------------------------------------------------------------------------- #
# Headless render (Playwright, optional)
# Captures media the static parser misses: JS-injected images, lazy-loaded ones,
# and CSS background-images. Also reads intrinsic dimensions straight from the DOM
# (naturalWidth/Height) and `img.currentSrc` — the srcset variant actually served
# at the chosen viewport. Optional dependency: pip install playwright && playwright install chromium
# --------------------------------------------------------------------------- #
JS_COLLECT = r"""() => {
  const out = [];
  const push = (u, kind, extra) => { if (u && u.indexOf('data:') !== 0) out.push(Object.assign({url: u, kind: kind}, extra || {})); };
  document.querySelectorAll('img').forEach(img =>
    push(img.currentSrc || img.src, 'image', {alt: img.alt || '', title: img.title || '', nw: img.naturalWidth || 0, nh: img.naturalHeight || 0}));
  document.querySelectorAll('video').forEach(v => {
    push(v.currentSrc || v.src, 'video', {nw: v.videoWidth || 0, nh: v.videoHeight || 0});
    if (v.poster) push(v.poster, 'image', {});
  });
  document.querySelectorAll('source').forEach(s => { if (s.src) push(s.src, 'media', {}); });
  document.querySelectorAll('*').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg.indexOf('url(') >= 0) {
      const re = /url\((['"]?)(.*?)\1\)/g; let m;
      while ((m = re.exec(bg))) push(m[2], 'image', {});
    }
  });
  return {assets: out, bodyClass: (document.body && document.body.className) || ''};
}"""


def start_browser(viewport):
    """Return (playwright, browser, page) or None if Playwright isn't available."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]},
                              user_agent=UA, device_scale_factor=1)
    return pw, browser, ctx.new_page()


def render_page_assets(page, page_url, quiet):
    """Render page_url in the headless browser and return (found, meta, body_class),
    matching extract_assets() but from the live DOM (meta also carries nw/nh)."""
    try:
        page.goto(page_url, wait_until="networkidle", timeout=30000)
    except Exception:
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            return [], {}, ""
    try:  # auto-scroll to trigger lazy-loading
        page.evaluate("""async () => { await new Promise(res => {
            let y = 0, n = 0; const step = Math.max(300, window.innerHeight);
            const t = setInterval(() => { window.scrollBy(0, step); y += step; n++;
              if (y >= document.body.scrollHeight || n > 40) { clearInterval(t); res(); } }, 80);
        }); }""")
        page.wait_for_timeout(700)
    except Exception:
        pass
    try:
        data = page.evaluate(JS_COLLECT)
    except Exception:
        return [], {}, ""
    seen, meta = {}, {}
    for a in data.get("assets", []):
        url = urldefrag(urljoin(page_url, a.get("url") or ""))[0]
        if not url or url.startswith("data:"):
            continue
        seen.setdefault(url, a.get("kind") or "image")
        m = meta.setdefault(url, {})
        for k in ("alt", "title", "nw", "nh"):
            v = a.get(k)
            if v and not m.get(k):
                m[k] = v
    return list(seen.items()), meta, data.get("bodyClass", "")


def merge_found(assets, found, meta_by_url, page):
    """Merge a page's (found, meta) into the global assets dict."""
    for url, kind in found:
        e = assets.setdefault(url, {"kind": kind, "pages": set(), "alt": "", "title": "", "nw": 0, "nh": 0})
        e["pages"].add(page)
        m = meta_by_url.get(url) or {}
        if m.get("alt") and not e["alt"]:
            e["alt"] = m["alt"]
        if m.get("title") and not e["title"]:
            e["title"] = m["title"]
        if m.get("nw") and not e.get("nw"):
            e["nw"], e["nh"] = m["nw"], m.get("nh", 0)


# --------------------------------------------------------------------------- #
# Checkpoint (resume after a block/interruption without re-scanning pages)
# --------------------------------------------------------------------------- #
def save_manifest(path, assets, page_cms):
    data = {"assets": {u: {**m, "pages": sorted(m["pages"])} for u, m in assets.items()},
            "page_cms": page_cms}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assets = {u: {**m, "pages": set(m["pages"])} for u, m in data["assets"].items()}
    return assets, data.get("page_cms", {})


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Census images & videos of a website.")
    ap.add_argument("--url", required=True, help="Target URL (page or site root)")
    ap.add_argument("--site", action="store_true", help="Crawl whole site (sitemap, fallback link crawl)")
    ap.add_argument("--pages", nargs="*", help="Explicit list of page URLs to scan")
    ap.add_argument("--pages-file", help="File with one page URL per line (cleaner than --pages for big lists)")
    ap.add_argument("--resume", action="store_true",
                    help="Resume from a previous run's checkpoint (.manifest.json in --out): "
                         "skips page scanning, reuses the cached downloads. Ideal after a WAF block.")
    ap.add_argument("--out", default="media-inventory-out", help="Output directory")
    ap.add_argument("--max-pages", type=int, default=50)
    ap.add_argument("--rpm", type=int, default=30,
                    help="Max requests per minute (global rate limit; keep low to avoid "
                         "WAF/Wordfence blocks). 30 = one request every 2s.")
    ap.add_argument("--throttle", type=float, default=0.0,
                    help="Extra floor on seconds between requests (usually leave 0; --rpm governs)")
    ap.add_argument("--no-download", action="store_true", help="Skip downloads (no px for images)")
    ap.add_argument("--render", action="store_true",
                    help="Render each page in a headless browser (Playwright) to catch JS-injected, "
                         "lazy-loaded and CSS background images, read intrinsic dimensions from the DOM, "
                         "and record the srcset variant actually served. Needs: pip install playwright "
                         "&& playwright install chromium. Falls back to static scraping if unavailable.")
    ap.add_argument("--viewport", default="1440x900",
                    help="Viewport WxH for --render (default 1440x900); also sets which srcset variant "
                         "is captured as served.")
    ap.add_argument("--source", choices=["scrape", "auto", "wp-api", "shopify", "payload"], default="scrape",
                    help="scrape (default) = crawl pages; auto = use the CMS media API if detected, "
                         "else scrape; wp-api/shopify = force that adapter. API modes pull the CMS "
                         "media library (reliable upload_date/alt/dimensions, far fewer requests → "
                         "avoids WAF blocks) but yield no per-page usage/template data.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    quiet = args.quiet
    _RATE["interval"] = max(60.0 / max(1, args.rpm), args.throttle)
    log(f"Rate limit: ~{args.rpm} req/min ({_RATE['interval']:.1f}s between requests)", quiet)
    try:
        viewport = tuple(int(x) for x in args.viewport.lower().split("x"))
        assert len(viewport) == 2
    except (ValueError, AssertionError):
        viewport = (1440, 900)

    # CMS API mode (authoritative library; few requests; no per-page usage)
    if args.source != "scrape":
        src = {"wp-api": "wordpress", "shopify": "shopify", "payload": "payload", "auto": "auto"}[args.source]
        api_records = inventory_via_api(args.url, src, quiet)
        if api_records:
            csv_path = os.path.join(args.out, "inventory.csv")
            md_path = os.path.join(args.out, "inventory.md")
            write_csv(csv_path, api_records)
            write_md(md_path, api_records, args.url, 0, {})  # n_pages=0 -> "CMS media library"
            log(f"\nDone (CMS API). {len(api_records)} assets.", quiet)
            print(f"CSV: {csv_path}")
            print(f"MD:  {md_path}")
            return
        if args.source != "auto":
            log("Requested API source unavailable — falling back to scraping.", quiet)
        # auto, or forced adapter that returned nothing -> fall through to scraping

    manifest_path = os.path.join(args.out, ".manifest.json")
    assets: dict[str, dict] = {}   # url -> {kind, pages:set, alt, title}
    page_cms: dict[str, str] = {}  # page url -> CMS template (body class)

    # merge explicit pages (--pages and/or --pages-file)
    pages_arg = list(args.pages) if args.pages else []
    if args.pages_file:
        with open(args.pages_file, encoding="utf-8") as f:
            pages_arg += [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    explicit = bool(pages_arg)

    # 0. Resume from checkpoint (skip page scanning entirely)
    if args.resume and os.path.exists(manifest_path):
        assets, page_cms = load_manifest(manifest_path)
        log(f"Resume: checkpoint loaded — {len(assets)} assets from {len(page_cms)} pages, "
            "skipping phase 1 (also reusing the downloads in .cache).", quiet)
    else:
        if args.resume:
            log("No checkpoint found: running a full scan.", quiet)
        # 1. Determine pages
        if explicit:
            pages = pages_arg
        elif args.site:
            log("Discovering pages via sitemap…", quiet)
            pages = discover_via_sitemap(args.url, quiet)
            if not pages:
                log("No sitemap; falling back to link crawl…", quiet)
                pages = discover_via_crawl(args.url, args.max_pages, args.throttle, quiet)
        else:
            pages = [args.url]
        pages = list(dict.fromkeys(pages))
        if not explicit:  # --max-pages only caps auto-discovery, never an explicit list
            pages = pages[: args.max_pages]
        log(f"Pages to scan: {len(pages)}", quiet)

        # 2. Extract assets per page (static, or headless render with --render)
        failed_pages: list[str] = []
        browser_state = start_browser(viewport) if args.render else None
        if args.render and browser_state is None:
            log("--render: Playwright not available; using static scraping. "
                "Install with: pip install playwright && playwright install chromium", quiet)
        bpage = browser_state[2] if browser_state else None
        try:
            for i, page in enumerate(pages, 1):
                if bpage is not None:
                    found, meta_by_url, body_class = render_page_assets(bpage, page, quiet)
                    if not found and not body_class:
                        failed_pages.append(page)
                        log(f"  [{i}/{len(pages)}] render failed: {page}", quiet)
                        time.sleep(_RATE["interval"])
                        continue
                    page_cms[page] = template_cms_label(body_class)
                    merge_found(assets, found, meta_by_url, page)
                    log(f"  [{i}/{len(pages)}] {page} -> {len(found)} assets (tot {len(assets)})", quiet)
                    time.sleep(_RATE["interval"])  # polite pacing between page loads
                    continue
                status, headers, body = http_get(page)
                ctype = headers.get("content-type", "")
                if not body:
                    failed_pages.append(page)
                    log(f"  [{i}/{len(pages)}] FETCH FAILED ({status or headers.get('_error', '?')}): {page}", quiet)
                    if blocked_too_much():
                        log("\n*** The server is rate-limiting us (repeated 429/503). Stopping the "
                            "scan. Resume later with --resume (or lower --rpm). ***", quiet)
                        break
                    continue
                if "html" not in ctype:
                    log(f"  [{i}/{len(pages)}] skip (non-HTML, {ctype.split(';')[0]}): {page}", quiet)
                    continue
                found, meta_by_url, body_class = extract_assets(page, body)
                page_cms[page] = template_cms_label(body_class)
                merge_found(assets, found, meta_by_url, page)
                log(f"  [{i}/{len(pages)}] {page} -> {len(found)} assets (tot {len(assets)})", quiet)
        finally:
            if browser_state:
                try:
                    browser_state[1].close()
                    browser_state[0].stop()
                except Exception:
                    pass

        if failed_pages:
            log(f"\n⚠ {len(failed_pages)} pages not fetched.", quiet)
        # checkpoint phase 1 so a later block doesn't force a re-scan
        save_manifest(manifest_path, assets, page_cms)

    log(f"Unique assets: {len(assets)}. Probing…", quiet)

    # 3. Probe each unique asset
    records = []
    for j, (url, meta) in enumerate(assets.items(), 1):
        if blocked_too_much():
            log(f"\n*** Persistent rate-limit (429/503) during probing at {j}/{len(assets)}. "
                "Stopping: downloads so far are in .cache and phase 1 in the checkpoint — "
                "resume with --resume. ***", quiet)
            break
        rec = probe_asset(url, meta["kind"], args.out, not args.no_download, quiet)
        rec["source_pages"] = meta["pages"]
        rec["alt"] = meta.get("alt", "")
        rec["title"] = meta.get("title", "")
        # fall back to DOM-intrinsic dimensions (from --render) when probing didn't get them
        if not rec.get("width_px") and meta.get("nw"):
            rec["width_px"], rec["height_px"] = meta["nw"], meta.get("nh", "")
        derive_fields(rec)
        pgs = meta["pages"]
        rec["template_url"] = ", ".join(sorted({template_of(p) for p in pgs}))
        rec["template_cms"] = ", ".join(sorted({page_cms.get(p, "?") for p in pgs}))
        records.append(rec)
        if j % 20 == 0:
            log(f"  probed {j}/{len(assets)}", quiet)

    # 4. Write outputs
    csv_path = os.path.join(args.out, "inventory.csv")
    md_path = os.path.join(args.out, "inventory.md")
    write_csv(csv_path, records)
    write_md(md_path, records, args.url, len(page_cms) or len(assets), page_cms)
    per_template, per_template_cms, per_page, fmts = format_breakdown(records, page_cms)
    write_breakdown_csv(os.path.join(args.out, "formats_by_template.csv"), per_template, fmts, "template_url")
    write_breakdown_csv(os.path.join(args.out, "formats_by_template_cms.csv"), per_template_cms, fmts, "template_cms")
    write_breakdown_csv(os.path.join(args.out, "formats_by_page.csv"), per_page, fmts, "page")
    log(f"\nDone. {len(records)} assets.", quiet)
    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    print(f"Breakdown: {os.path.join(args.out, 'formats_by_template.csv')} (+ _cms, _by_page)")


if __name__ == "__main__":
    main()
