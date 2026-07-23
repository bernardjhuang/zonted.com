#!/usr/bin/env python3
"""Inject tail-risk brief log into trading/index.html (AUTO:BRIEF block).

Reads ALL briefs from tail-risk-scanner/briefs/*.md, renders them newest-first
as a running log inside the Brief tab.

Supports two brief formats:
- v1.x structured format: numbered items with indented Score/Evidence/Levers fields
- v1.3+ rich markdown format: ## headers, **bold** sections, markdown tables, bullet lists

The newest brief is fully expanded; older briefs are collapsed behind a disclosure triangle.
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
    """Escape HTML first, then apply inline formatting."""
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def score_color(score):
    try:
        s = float(score)
    except (ValueError, TypeError):
        return "var(--bl-faint)"
    if s >= 4.0:
        return "var(--bl-loss)"
    elif s >= 3.0:
        return "#c97a1d"
    else:
        return "var(--bl-faint)"


def evidence_color(level):
    level = level.upper()
    if level == "HIGH":
        return "var(--bl-loss)"
    elif level == "MED":
        return "#c97a1d"
    else:
        return "var(--bl-faint)"


# ---------------------------------------------------------------------------
# Markdown block parsers (table, bullet list)
# ---------------------------------------------------------------------------

def parse_table_block(lines, start_idx):
    """Parse consecutive lines starting with | into a table. Returns (html, end_idx)."""
    rows = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        # Skip separator lines (|---|---|)
        if re.match(r"^\|[\s\-:|]+\|$", line):
            i += 1
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)
        i += 1

    if not rows:
        return "", start_idx

    header = rows[0]
    data_rows = rows[1:]

    parts = ['<div class="brief-table-wrap"><table class="brief-table"><thead><tr>']
    for cell in header:
        parts.append(f"<th>{safe_inline(cell)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in data_rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{safe_inline(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts), i


def parse_bullet_list(lines, start_idx):
    """Parse consecutive bullet lines into a <ul>. Returns (html, end_idx)."""
    items = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^[-•]\s+(.+)", line)
        if not m:
            break
        items.append(m.group(1))
        i += 1

    if not items:
        return "", start_idx

    lis = "".join(f"<li>{safe_inline(item)}</li>" for item in items)
    return f'<ul class="brief-bullets">{lis}</ul>', i


# ---------------------------------------------------------------------------
# Card / section renderers
# ---------------------------------------------------------------------------

def render_risk_card(num, title, body_lines):
    """Render a risk item as a card. Handles both old (field-based) and new (markdown) formats."""
    parts = ['<div class="brief-risk-card">']

    # Pre-scan for Score line to extract score badge
    score = "?"
    score_breakdown = ""
    score_line_idx = None
    for idx, line in enumerate(body_lines):
        if re.match(r"\s*Score:", line):
            m_score = re.search(r"→\s*\*{0,2}([\d.]+)\*{0,2}", line)
            if m_score:
                score = m_score.group(1)
            m_bd = re.match(r"\s*Score:\s*(.+?)\s*→", line)
            if m_bd:
                score_breakdown = m_bd.group(1).strip()
            score_line_idx = idx
            break

    sev_color = score_color(score)

    # Title + score badge
    parts.append(
        f'<div class="brief-card-header">'
        f'<h4 class="brief-risk-title"><span class="brief-num">{esc(num)}.</span> {safe_inline(title)}</h4>'
        f'<span class="brief-score-badge" style="background:{sev_color}">⚠️ {esc(score)}</span>'
        f'</div>'
    )

    if score_breakdown:
        # Convert pipe separators to middots for cleaner display
        bd = score_breakdown.replace("|", "·")
        parts.append(f'<small class="brief-score-detail">{safe_inline(bd)}</small>')

    # Process body lines
    i = 0
    while i < len(body_lines):
        line = body_lines[i]
        stripped = line.strip()

        # Score line already rendered
        if i == score_line_idx:
            i += 1
            continue

        if not stripped or stripped == "---":
            i += 1
            continue

        # Old structured format: Evidence
        m_ev = re.match(r"\s*Evidence:\s*(\w+)\s*·\s*Sources:\s*(.+)", line)
        if m_ev:
            level = m_ev.group(1).upper()
            sources = m_ev.group(2).strip()
            ev_color = evidence_color(level)
            parts.append(
                f'<div class="brief-section">'
                f'<span class="brief-evidence-tag" style="background:{ev_color}">{esc(level)}</span>'
                f'<small class="brief-sources">{safe_inline(sources)}</small>'
                f'</div>'
            )
            i += 1
            continue

        m_ev2 = re.match(r"\s*Evidence:\s*(\w+)", line)
        if m_ev2:
            level = m_ev2.group(1).upper()
            ev_color = evidence_color(level)
            parts.append(
                f'<div class="brief-section">'
                f'<span class="brief-evidence-tag" style="background:{ev_color}">{esc(level)}</span>'
                f'</div>'
            )
            i += 1
            continue

        # Old structured format: Levers
        m_lev = re.match(r"\s*Levers:\s*(.+)", line)
        if m_lev:
            tickers = [t.strip() for t in m_lev.group(1).split(",") if t.strip()]
            if tickers:
                chips = "".join(f'<code class="brief-ticker">{esc(t)}</code>' for t in tickers)
                parts.append(f'<div class="brief-levers">{chips}</div>')
            i += 1
            continue

        # Old structured format: Merged legs
        m_ml = re.match(r"\s*Merged legs:\s*(.+)", line)
        if m_ml:
            parts.append(
                f'<details class="brief-details"><summary>Technical details</summary>'
                f'<div class="brief-details-body"><p>{safe_inline(m_ml.group(1).strip())}</p></div></details>'
            )
            i += 1
            continue

        # Old structured format: Disconfirm
        m_dc = re.match(r"\s*Disconfirm:\s*(.+)", line)
        if m_dc:
            parts.append(
                f'<div class="brief-section">'
                f'<span class="brief-label">❌ What would prove this wrong:</span>'
                f' {safe_inline(m_dc.group(1).strip())}'
                f'</div>'
            )
            i += 1
            continue

        # Old structured format: If true
        m_it = re.match(r"\s*If true\s*→\s*(.+)", line)
        if m_it:
            parts.append(
                f'<div class="brief-section">'
                f'<span class="brief-label">✅ If this plays out:</span>'
                f' {safe_inline(m_it.group(1).strip())}'
                f'</div>'
            )
            i += 1
            continue

        # Old structured format: Watch
        m_w = re.match(r"\s*Watch:\s*(.+)", line)
        if m_w:
            watch_items = [s.strip() for s in re.split(r";\s*", m_w.group(1)) if s.strip()]
            if watch_items:
                bullets = "".join(f"<li>{safe_inline(item)}</li>" for item in watch_items)
                parts.append(
                    f'<div class="brief-section brief-signals">'
                    f'<span class="brief-label">📊 Key signals to watch:</span>'
                    f'<ul>{bullets}</ul>'
                    f'</div>'
                )
            i += 1
            continue

        # Markdown table
        if stripped.startswith("|"):
            table_html, new_i = parse_table_block(body_lines, i)
            if table_html:
                parts.append(table_html)
                i = new_i
                continue
            # Fall through if table parse failed

        # Bullet list
        if re.match(r"^[-•]\s+", stripped):
            list_html, new_i = parse_bullet_list(body_lines, i)
            if list_html:
                parts.append(list_html)
                i = new_i
                continue

        # Regular paragraph (handles **bold:** labels, plain text, links)
        parts.append(f'<p class="brief-para">{safe_inline(stripped)}</p>')
        i += 1

    parts.append('</div>')
    return "\n".join(parts)


def render_collapsed_section(title, body_lines):
    """Render a collapsed <details> section (Dropped/merged, Process, Technical details, etc.)."""
    label_map = {
        "dropped": "🗑️ Dropped / merged items",
        "merged": "🗑️ Dropped / merged items",
        "underpricing": "📋 Underpricing checklist",
        "finra": "📊 FINRA short volume",
        "process": "⚙️ Process notes",
        "technical": "⚙️ Technical details",
    }
    label = "Technical details"
    for key, val in label_map.items():
        if key in title.lower():
            label = val
            break

    parts = [f'<details class="brief-details"><summary>{esc(label)}</summary><div class="brief-details-body">']

    i = 0
    while i < len(body_lines):
        line = body_lines[i]
        stripped = line.strip()

        # Filter out raw <details>/< /details> HTML tags from markdown
        if stripped in ("<details>", "</details>"):
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        # Table
        if stripped.startswith("|"):
            table_html, new_i = parse_table_block(body_lines, i)
            if table_html:
                parts.append(table_html)
                i = new_i
                continue

        # Bullet list
        if re.match(r"^[-•]\s+", stripped):
            list_html, new_i = parse_bullet_list(body_lines, i)
            if list_html:
                parts.append(list_html)
                i = new_i
                continue

        parts.append(f'<p>{safe_inline(stripped)}</p>')
        i += 1

    parts.append('</div></details>')
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main brief body parser
# ---------------------------------------------------------------------------

def parse_brief_body(raw):
    """Parse raw brief markdown into structured HTML."""
    lines = raw.split("\n")
    output = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip metadata header lines
        if stripped.startswith("Date:") or stripped.startswith("Tail-Risk Brief") or stripped.startswith("Note:"):
            i += 1
            continue

        if not stripped or stripped == "---":
            i += 1
            continue

        # Numbered item header: ## N. Title or N. Title
        m_num = re.match(r"^#{0,2}\s*(\d+)\.\s+(.+)", stripped)
        if m_num:
            num = m_num.group(1)
            title = m_num.group(2).strip()
            body = []
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if re.match(r"^#{0,2}\s*\d+\.\s+", nxt):
                    break
                if re.match(r"^#{1,3}\s+(Dropped|Merged|Technical|Underpricing|FINRA|Process)", nxt, re.I):
                    break
                if re.match(r"^(Dropped|Merged|Technical\s+details|Underpricing|FINRA|Process)\s*[:/]", nxt, re.I):
                    break
                body.append(lines[i])
                i += 1
            output.append(render_risk_card(num, title, body))
            continue

        # ## Section header for collapsible content
        m_hd = re.match(r"^#{1,3}\s+(.+)", stripped)
        if m_hd:
            section_title = m_hd.group(1)
            if re.match(r"(Dropped|Merged|Technical|Underpricing|FINRA|Process)", section_title, re.I):
                body = []
                i += 1
                while i < len(lines):
                    nxt = lines[i].strip()
                    if re.match(r"^#{1,3}\s+", nxt):
                        break
                    if re.match(r"^#{0,2}\s*\d+\.\s+", nxt):
                        break
                    body.append(lines[i])
                    i += 1
                output.append(render_collapsed_section(section_title, body))
                continue
            # Non-collapsible header → render as h3
            output.append(f'<h3 class="brief-section-header">{safe_inline(section_title)}</h3>')
            i += 1
            continue

        # Old format section header without ## (Dropped:, Process:, etc.)
        m_old = re.match(r"^(Dropped|Merged|Technical\s+details|Underpricing|FINRA|Process)\s*[:/]", stripped, re.I)
        if m_old:
            section_title = m_old.group(1)
            body = []
            i += 1
            while i < len(lines):
                nxt = lines[i].strip()
                if re.match(r"^#{1,3}\s+", nxt):
                    break
                if re.match(r"^#{0,2}\s*\d+\.\s+", nxt):
                    break
                body.append(lines[i])
                i += 1
            output.append(render_collapsed_section(section_title, body))
            continue

        # Other standalone content — skip
        i += 1

    return "\n".join(output)


# ---------------------------------------------------------------------------
# Entry / CSS rendering
# ---------------------------------------------------------------------------

def format_date_human(date_str):
    try:
        d = dt.datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return d.strftime("%B %-d, %Y")
    except ValueError:
        return date_str


def render_brief_entry(path, is_newest=False):
    """Render a single brief .md file as an HTML <article> block."""
    raw = open(path).read()

    m = re.search(r"^Date:\s*(.+)$", raw, re.M)
    brief_date = m.group(1).strip() if m else os.path.basename(path).replace(".md", "")

    date_display = format_date_human(brief_date)
    body_html = parse_brief_body(raw)

    if is_newest:
        return (
            f'                <article class="brief-entry brief-entry-today" id="brief-{esc(brief_date)}">\n'
            f'                    <div class="brief-entry-header">\n'
            f'                        <h3>{esc(date_display)} — Morning Brief</h3>\n'
            f'                    </div>\n'
            f'                    <div class="brief-entry-body">\n'
            f'{body_html}\n'
            f'                    </div>\n'
            f'                </article>'
        )
    else:
        return (
            f'                <article class="brief-entry" id="brief-{esc(brief_date)}">\n'
            f'                    <details>\n'
            f'                        <summary><time datetime="{esc(brief_date)}">{esc(date_display)}</time></summary>\n'
            f'                        <div class="brief-entry-body">\n'
            f'{body_html}\n'
            f'                        </div>\n'
            f'                    </details>\n'
            f'                </article>'
        )


def build_brief_css():
    """Return CSS for brief cards, tables, and layout."""
    return """        .brief-entry-body { padding: 0 0 20px; font-size: 13.5px; line-height: 1.6; color: var(--bl-ink); }
        .brief-risk-card { border: 1px solid var(--bl-border); border-radius: 10px; padding: 16px 18px; margin: 12px 0; background: var(--bl-card); }
        .brief-card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
        .brief-risk-title { font-size: 15px; font-weight: 600; margin: 0 0 4px; line-height: 1.35; }
        .brief-num { color: var(--bl-faint); margin-right: 4px; }
        .brief-score-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font: 600 13px var(--bl-sans); color: #fff; white-space: nowrap; flex-shrink: 0; }
        .brief-score-detail { display: block; font: 400 11.5px var(--bl-mono); color: var(--bl-faint); margin: 2px 0 8px; }
        .brief-evidence-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font: 600 11px var(--bl-sans); color: #fff; text-transform: uppercase; letter-spacing: .03em; }
        .brief-sources { color: var(--bl-muted); margin-left: 8px; }
        .brief-levers { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0 10px; }
        .brief-ticker { font: 500 12px var(--bl-mono); background: var(--bl-chipbg); color: var(--bl-accent); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--bl-chipbd); }
        .brief-section { margin: 8px 0; }
        .brief-label { display: block; font-size: 12.5px; font-weight: 600; color: var(--bl-muted); margin-bottom: 3px; }
        .brief-signals ul, .brief-bullets { margin: 4px 0 6px; padding-left: 20px; }
        .brief-signals li, .brief-bullets li { margin: 3px 0; font-size: 13px; }
        .brief-para { margin: 6px 0; }
        .brief-section-header { font-size: 14px; font-weight: 600; margin: 16px 0 4px; color: var(--bl-muted); }
        .brief-table-wrap { overflow-x: auto; margin: 10px 0; }
        .brief-table { width: 100%; border-collapse: collapse; border-top: 1px solid var(--bl-border); font-size: 12.5px; }
        .brief-table th { background: var(--bl-rowhead, #f5f5f5); font: 600 11px var(--bl-sans); letter-spacing: .3px; text-transform: uppercase; color: var(--bl-muted); text-align: left; padding: 7px 10px; border-bottom: 0; white-space: nowrap; }
        .brief-table td { padding: 7px 10px; border-top: 1px solid var(--bl-divider, #eee); border-bottom: 0; white-space: normal; line-height: 1.5; font-variant-numeric: tabular-nums; }
        .brief-table tr:hover td { background: var(--bl-hover, #f9f9f9); }
        .brief-entry-today { border-left: 3px solid var(--bl-accent, #6366f1); padding-left: 12px; margin-left: -12px; }
        .brief-entry-header h3 { font-size: 17px; font-weight: 700; margin: 16px 0 4px; color: var(--bl-ink); }
        .brief-entry-header { border-bottom: 1px solid var(--bl-divider, #eee); padding-bottom: 8px; margin-bottom: 4px; }
        .brief-details { margin-top: 10px; border-top: 1px dashed var(--bl-divider, #ddd); padding-top: 8px; }
        .brief-details > summary { cursor: pointer; font-size: 12px; color: var(--bl-faint); list-style: none; }
        .brief-details > summary::before { content: '▸ '; }
        .brief-details[open] > summary::before { content: '▾ '; }
        .brief-details-body { padding: 6px 0; font-size: 12px; color: var(--bl-muted); }
        .brief-details-body p { margin: 3px 0; }
        .brief-details-body .brief-bullets { font-size: 12px; }
        .brief-details-body .brief-bullets li { font-size: 12px; }"""


def main():
    # Collect all brief files, newest first
    all_paths = sorted(set(glob.glob(BRIEF_GLOB_PRIMARY) + glob.glob(BRIEF_GLOB_FALLBACK)), reverse=True)

    if not all_paths:
        sys.exit("No brief *.md found")

    # Render each brief — newest is fully expanded, rest are collapsed
    entries = [render_brief_entry(p, is_newest=(idx == 0)) for idx, p in enumerate(all_paths)]
    entries_html = "\n\n".join(entries)

    latest_date = os.path.basename(all_paths[0]).replace(".md", "")
    latest_display = format_date_human(latest_date)
    entry_count = len(all_paths)

    panel_lines = [
        '            <section class="trading-panel brief-panel" id="brief-panel" role="tabpanel" tabindex="0" aria-labelledby="brief-tab" hidden>',
        '                <div class="position-head">',
        '                    <h2 id="brief-heading">Morning Brief</h2>',
        f'                    <span>{entry_count} briefs · latest {esc(latest_display)} · pre-market CT</span>',
        '                </div>',
        "                <p class=\"trading-takeaway\">Daily tail-risk research in plain English. Each card breaks down what's happening, what could prove it wrong, and what to watch. Newest first.</p>",
        '                <div class="brief-log">',
        entries_html,
        '                </div>',
        '                <p class="trading-note">Research and idea generation only. Not trade recommendations or investment advice.</p>',
        '            </section>',
    ]
    panel = "\n".join(panel_lines)

    page = open(PAGE).read()

    # Ensure tab button exists
    if 'id="brief-tab"' not in page:
        page = page.replace(
            '<button class="trading-tab" id="scan-tab"',
            '<button class="trading-tab" id="brief-tab" type="button" role="tab" aria-selected="false" aria-controls="brief-panel">Brief</button>\n                <button class="trading-tab" id="scan-tab"',
            1,
        )

    # Ensure AUTO:BRIEF markers exist
    if "<!-- AUTO:BRIEF:START -->" not in page:
        page = page.replace(
            "<!-- AUTO:WHALES:START -->",
            "<!-- AUTO:BRIEF:START -->\n            <!-- AUTO:BRIEF:END -->\n\n            <!-- AUTO:WHALES:START -->",
            1,
        )

    # --- CSS management ---
    brief_css = build_brief_css()

    # Replace everything between the summary-time anchor and the vwap-grid anchor
    # This cleanly handles old/duplicated CSS from prior runs
    css_anchor_start = ".brief-entry > details > summary time { font-variant-numeric: tabular-nums; }"
    css_anchor_end = ".bl .vwap-grid"
    css_re = re.compile(
        re.escape(css_anchor_start) + r".*?" + re.escape(css_anchor_end),
        re.S,
    )
    if css_re.search(page):
        page = css_re.sub(
            css_anchor_start + "\n" + brief_css + "\n\n        " + css_anchor_end,
            page,
            count=1,
        )
    else:
        # Fallback: inject before vwap-grid if anchor not found
        page = page.replace(css_anchor_end, brief_css + "\n\n        " + css_anchor_end, 1)

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
