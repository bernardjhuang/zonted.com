#!/usr/bin/env python3
"""Inject latest tail-risk brief into trading/index.html (AUTO:BRIEF block)."""
import datetime as dt
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
BRIEF_GLOB_PRIMARY = os.path.join(os.path.dirname(ROOT), "tail-risk-scanner", "briefs", "*.md")
BRIEF_GLOB_FALLBACK = os.path.expanduser("~/Documents/trading/briefs/*.md")


def esc(s):
    return html.escape(str(s or ""))


def safe_inline(text):
    """Escape HTML first, then apply inline formatting (bold, code)."""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def md_to_html(text):
    """Simple regex-based markdown → HTML converter for brief content."""
    lines = text.split("\n")
    out = []
    in_ul = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw_line in lines:
        line = raw_line.rstrip()

        # Skip metadata header lines
        if line.startswith("Date:") or line.startswith("Tail-Risk Brief v"):
            continue

        # Blank line → <br>
        if not line.strip():
            close_ul()
            out.append("<br>")
            continue

        # ## heading → <h3>
        m = re.match(r"^##\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h3>{esc(m.group(1))}</h3>")
            continue

        # ### heading → <h4>
        m = re.match(r"^###\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h4>{esc(m.group(1))}</h4>")
            continue

        # # heading → <h3>
        m = re.match(r"^#\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h3>{esc(m.group(1))}</h3>")
            continue

        # Bullet lines: - or •
        m = re.match(r"^\s*[-•]\s+(.*)", line)
        if m:
            content = safe_inline(m.group(1))
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{content}</li>")
            continue

        # Numbered list lines: "1. Title..." → section heading
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            close_ul()
            num = m.group(1)
            content = safe_inline(m.group(2))
            out.append(f'<h3><span class="brief-num">{num}.</span> {content}</h3>')
            continue

        # Regular paragraph line
        close_ul()
        out.append(f"<p>{safe_inline(line)}</p>")

    close_ul()
    return "\n".join(out)


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        paths = sorted(glob.glob(BRIEF_GLOB_PRIMARY) + glob.glob(BRIEF_GLOB_FALLBACK))
        if not paths:
            sys.exit("No brief *.md found")
        path = paths[-1]

    raw = open(path).read()

    # Extract date from the brief or filename
    m = re.search(r"^Date:\s*(.+)$", raw, re.M)
    if m:
        brief_date = m.group(1).strip()
    else:
        brief_date = os.path.basename(path).replace(".md", "")

    body_html = md_to_html(raw)

    panel_lines = [
        '            <section class="trading-panel brief-panel" id="brief-panel" role="tabpanel" tabindex="0" aria-labelledby="brief-tab" hidden>',
        '                <div class="position-head">',
        '                    <h2 id="brief-heading">Morning Brief</h2>',
        f'                    <span>{esc(brief_date)} · pre-market CT</span>',
        '                </div>',
        '                <div class="brief-content">',
        body_html,
        '                </div>',
        '                <p class="trading-note">Research and idea generation only. Not trade recommendations or investment advice.</p>',
        '            </section>',
    ]
    panel = "\n".join(panel_lines)

    page = open(PAGE).read()

    # Ensure tab button exists (after congress tab, before whales tab)
    if 'id="brief-tab"' not in page:
        page = page.replace(
            '<button class="trading-tab" id="whales-tab"',
            '<button class="trading-tab" id="brief-tab" type="button" role="tab" aria-selected="false" aria-controls="brief-panel">Brief</button>\n                <button class="trading-tab" id="whales-tab"',
            1,
        )

    # Ensure AUTO:BRIEF markers exist (between CONGRESS:END and WHALES:START)
    if "<!-- AUTO:BRIEF:START -->" not in page:
        page = page.replace(
            "<!-- AUTO:WHALES:START -->",
            "<!-- AUTO:BRIEF:START -->\n            <!-- AUTO:BRIEF:END -->\n\n            <!-- AUTO:WHALES:START -->",
            1,
        )

    # Inject panel between markers
    new = re.sub(
        r"(<!-- AUTO:BRIEF:START -->).*?(<!-- AUTO:BRIEF:END -->)",
        lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
        page,
        flags=re.S,
    )

    if new == open(PAGE).read():
        print(f"[brief] already current: {os.path.basename(path)}")
        return

    open(PAGE, "w").write(new)
    print(f"[brief] injected {os.path.basename(path)} ({brief_date})")


if __name__ == "__main__":
    main()
