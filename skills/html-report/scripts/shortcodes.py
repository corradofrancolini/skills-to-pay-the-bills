"""
Post-process the pandoc HTML body to finish the rich blocks that pandoc's
fenced_divs/bracketed_spans can't fully shape. All functions are idempotent and
operate on an HTML string.

Pandoc already does most of the work:
  ::: callout                 -> <div class="callout">
  ::: {.callout .callout-green} -> <div class="callout callout-green">
  ::: tldr                    -> <div class="tldr">
  [Stable]{.badge .badge-stable} -> <span class="badge badge-stable">Stable</span>
  [PASS]{.ok}                 -> <span class="ok">PASS</span>
Raw <details> conversation blocks pass through untouched.

This module only handles the two cases that need structural tweaks:
  1. callout color variants  -> inline style + drop the modifier class
  2. .ct-title promotion      (leading <p><strong>..</strong></p> inside a callout)
  3. .verdict-line            (a <p> inside .tldr that contains a label-verdict span)
"""
import re

# color name -> inline style mirroring the reference report's green callout
CALLOUT_VARIANTS = {
    "callout-green": "border-left-color:#1b5e20; background:#e8f5e9;",
    "callout-blue":  "border-left-color:#1565c0; background:#e3f2fd;",
    "callout-red":   "border-left-color:#c62828; background:#ffebee;",
}


def _process_callout(open_tag_classes: str, inner: str) -> str:
    """Build a <div class="callout"[ style]> ... </div> from the matched class list + inner HTML."""
    classes = open_tag_classes.split()
    style = ""
    for variant, css in CALLOUT_VARIANTS.items():
        if variant in classes:
            style = f' style="{css}"'
            classes = [c for c in classes if c != variant]
            break
    # promote a leading bold line to <div class="ct-title">. Handles both
    #   <p><strong>Title</strong></p><p>body</p>      (blank line after title)
    #   <p><strong>Title</strong> body...</p>          (title + body same paragraph)
    inner = inner.strip()
    if "ct-title" not in inner[:40]:
        m = re.match(r'\s*<p>\s*<strong>(.*?)</strong>(.*?)</p>(.*)', inner, re.S)
        if m:
            title, rest, more = m.group(1).strip(), m.group(2).strip(), m.group(3)
            body = (f"<p>{rest}</p>" if rest else "") + more
            inner = f'<div class="ct-title">{title}</div>{body}'
    cls = " ".join(classes) if classes else "callout"
    return f'<div class="{cls}"{style}>{inner}</div>'


def expand_callouts(html: str) -> str:
    # Match <div class="callout ..."> ... </div> (non-greedy, no nested .callout expected)
    pattern = re.compile(r'<div class="(callout[^"]*)">(.*?)</div>', re.S)
    # iterate until stable (idempotent); one pass is enough for non-nested callouts
    return pattern.sub(lambda m: _process_callout(m.group(1), m.group(2)), html)


def mark_verdict_line(html: str) -> str:
    """Inside each <div class="tldr">...</div>, add class="verdict-line" to any <p> containing label-verdict."""
    def fix_tldr(m):
        inner = m.group(1)
        inner = re.sub(
            r'<p>((?:(?!</p>).)*?label-verdict(?:(?!</p>).)*?)</p>',
            r'<p class="verdict-line">\1</p>',
            inner, flags=re.S,
        )
        return f'<div class="tldr">{inner}</div>'
    return re.sub(r'<div class="tldr">(.*?)</div>', fix_tldr, html, flags=re.S)


def process(html: str) -> str:
    html = expand_callouts(html)
    html = mark_verdict_line(html)
    return html
