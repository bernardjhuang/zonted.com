#!/usr/bin/env python3
"""Inject tail-risk brief log into trading/index.html (AUTO:BRIEF block).

Reads ALL briefs from tail-risk-scanner/briefs/*.md, renders them newest-first
as a running log inside the Brief tab.
"""
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
    """Simple regex-based markdown to HTML converter for brief content."""
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

        # Skip metadata header lines (Date: and Tail-Risk Brief v...)
        if line.startswith("Date:") or line.startswith("Tail-Risk Brief v"):
            continue

        # Blank line
        if not line.strip():
            close_ul()
            continue

        # ## heading
        m = re.match(r"^##\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h4>{esc(m.group(1))}</h4>")
            continue

        # ### heading
        m = re.match(r"^###\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h4>{esc(m.group(1))}</h4>")
            continue

        # # heading
        m = re.match(r"^#\s+(.*)", line)
        if m:
            close_ul()
            out.append(f"<h4>{esc(m.group(1))}</h4>")
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

        # Numbered list lines: "1. Title..." → subsection heading
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            close_ul()
            num = m.group(1)
            content = safe_inline(m.group(2))
            out.append(f'<h4 class="brief-item"><span class="brief-num">{num}.</span> {content}</h4>')
            continue

        # Regular paragraph line
        close_ul()
        out.append(f"<p>{safe_inline(line)}</p>")

    close_ul()
    return "\n".join(out)


def render_brief_entry(path):
    """Render a single brief .md file as an HTML <article> block."""
    raw = open(path).read()

    # Extract date
    m = re.search(r"^Date:\s*(.+)$", raw, re.M)
    if m:
        brief_date = m.group(1).strip()
    else:
        brief_date = os.path.basename(path).replace(".md", "")

    body_html = md_to_html(raw)

    return (
        f'                <article class="brief-entry" id="brief-{esc(brief_date)}">\n'
        f'                    <details open>\n'
        f'                        <summary><time datetime="{esc(brief_date)}">{esc(brief_date)}</time></summary>\n'
        f'                        <div class="brief-entry-body">\n'
        f'{body_html}\n'
        f'                        </div>\n'
        f'                    </details>\n'
        f'                </article>'
    )


def main():
    # Collect all brief files from both locations, dedupe, sort newest-first
    all_paths = set(glob.glob(BRIEF_GLOB_PRIMARY) + glob.glob(BRIEF_GLOB_FALLBACK))
    all_paths = sorted(all_paths, reverse=True)  # newest filename first (YYYY-MM-DD.md)

    if not all_paths:
        sys.exit("No brief *.md found")

    # Render each brief as an article, newest first
    entries = [render_brief_entry(p) for p in all_paths]
    entries_html = "\n\n".join(entries)

    latest_date = os.path.basename(all_paths[0]).replace(".md", "")
    entry_count = len(all_paths)

    panel_lines = [
        '            <section class="trading-panel brief-panel" id="brief-panel" role="tabpanel" tabindex="0" aria-labelledby="brief-tab" hidden>',
        '                <div class="position-head">',
        '                    <h2 id="brief-heading">Morning Brief</h2>',
        f'                    <span>{entry_count} briefs · latest {esc(latest_date)} · pre-market CT</span>',
        '                </div>',
        '                <p class="trading-takeaway">Daily tail-risk + event-catalyst research brief. Newest first. Each entry is collapsible.</p>',
        '                <div class="brief-log">',
        entries_html,
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

    # Ensure AUTO:BRIEF markers exist
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
        print(f"[brief] already current: {entry_count} briefs, latest {latest_date}")
        return

    open(PAGE, "w").write(new)
    print(f"[brief] injected {entry_count} briefs, latest {latest_date}")


if __name__ == "__main__":
    main()
