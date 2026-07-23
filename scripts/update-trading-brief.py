#!/usr/bin/env python3
"""Inject tail-risk brief log into trading/index.html (AUTO:BRIEF block).

Reads ALL briefs from tail-risk-scanner/briefs/*.md, renders them newest-first
as a running log inside the Brief tab.

Each brief is transformed from raw markdown into clean, ELI5 card-based HTML:
- Numbered risk items become "risk cards" with score badges, ticker chips,
  evidence tags, and labeled sections for disconfirmation / action / signals.
- Process notes, FINRA tables, underpricing checklists collapse into a details block.
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


def score_color(score):
    """Return a severity color based on composite score."""
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
    """Return color for evidence level."""
    level = level.upper()
    if level == "HIGH":
        return "var(--bl-loss)"
    elif level == "MED":
        return "#c97a1d"
    else:
        return "var(--bl-faint)"


def parse_score_line(line):
    """Extract composite score and breakdown from Score: line."""
    # Score: I5 (...) | U3 (...) | A5 (...) → 4.3
    m = re.search(r"→\s*([\d.]+)", line)
    composite = m.group(1) if m else "?"
    # Extract the I/U/A breakdown (everything between Score: and →)
    m2 = re.match(r"\s*Score:\s*(.+?)\s*→", line)
    breakdown = m2.group(1).strip() if m2 else ""
    return composite, breakdown


def parse_evidence_line(line):
    """Extract evidence level and sources."""
    # Evidence: HIGH · Sources: ...
    m = re.match(r"\s*Evidence:\s*(\w+)\s*·\s*Sources:\s*(.+)", line)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    m2 = re.match(r"\s*Evidence:\s*(\w+)", line)
    if m2:
        return m2.group(1).upper(), ""
    return "", ""


def parse_levers_line(line):
    """Extract ticker list from Levers: line."""
    m = re.match(r"\s*Levers:\s*(.+)", line)
    if not m:
        return []
    raw = m.group(1).strip()
    # Split on commas, clean up
    tickers = [t.strip() for t in raw.split(",") if t.strip()]
    return tickers


def render_ticker_chips(tickers):
    """Render ticker list as code chips."""
    if not tickers:
        return ""
    chips = "".join(f'<code class="brief-ticker">{esc(t)}</code>' for t in tickers)
    return f'<div class="brief-levers">{chips}</div>'


def render_watch_line(line):
    """Render the Watch: line as a bulleted signals list."""
    m = re.match(r"\s*Watch:\s*(.+)", line)
    if not m:
        return ""
    items = [s.strip() for s in re.split(r";\s*", m.group(1)) if s.strip()]
    if not items:
        return ""
    bullets = "".join(f"<li>{safe_inline(item)}</li>" for item in items)
    return f'<div class="brief-section brief-signals"><span class="brief-label">📊 Key signals to watch:</span><ul>{bullets}</ul></div>'


def render_risk_card(num, title, fields, extra_lines):
    """Render a single risk item as a card."""
    composite = fields.get("composite", "?")
    breakdown = fields.get("breakdown", "")
    evidence_level = fields.get("evidence_level", "")
    evidence_sources = fields.get("evidence_sources", "")
    levers = fields.get("levers", [])
    disconfirm = fields.get("disconfirm", "")
    if_true = fields.get("if_true", "")
    watch_html = fields.get("watch_html", "")

    sev_color = score_color(composite)
    ev_color = evidence_color(evidence_level)

    parts = [f'<div class="brief-risk-card">']

    # Title row
    parts.append(
        f'<div class="brief-card-header">'
        f'<h4 class="brief-risk-title"><span class="brief-num">{num}.</span> {safe_inline(title)}</h4>'
        f'<span class="brief-score-badge" style="background:{sev_color}">⚠️ {esc(composite)}</span>'
        f'</div>'
    )

    # Score breakdown
    if breakdown:
        parts.append(f'<small class="brief-score-detail">{safe_inline(breakdown)}</small>')

    # Evidence tag + sources
    if evidence_level:
        parts.append(
            f'<div class="brief-section">'
            f'<span class="brief-evidence-tag" style="background:{ev_color}">{esc(evidence_level)}</span>'
            + (f'<small class="brief-sources">{safe_inline(evidence_sources)}</small>' if evidence_sources else "")
            + '</div>'
        )

    # Ticker chips
    if levers:
        parts.append(render_ticker_chips(levers))

    # Disconfirm
    if disconfirm:
        parts.append(
            f'<div class="brief-section">'
            f'<span class="brief-label">❌ <strong>What would prove this wrong:</strong></span> {safe_inline(disconfirm)}'
            f'</div>'
        )

    # If true
    if if_true:
        parts.append(
            f'<div class="brief-section">'
            f'<span class="brief-label">✅ <strong>If this plays out:</strong></span> {safe_inline(if_true)}'
            f'</div>'
        )

    # Watch
    if watch_html:
        parts.append(watch_html)

    # Extra lines (Merged legs etc.) collapsed
    if extra_lines:
        extra_html = "".join(f"<p>{safe_inline(l)}</p>" for l in extra_lines)
        parts.append(
            f'<details class="brief-details"><summary>Technical details</summary>'
            f'<div class="brief-details-body">{extra_html}</div></details>'
        )

    parts.append('</div>')
    return "\n".join(parts)


def parse_brief_body(raw):
    """Parse raw brief markdown into structured HTML.

    Returns HTML string for the brief entry body.
    """
    lines = raw.split("\n")
    output = []
    in_numbered_item = False
    current_num = None
    current_title = None
    current_fields = {}
    current_extra = []

    def flush_item():
        nonlocal in_numbered_item, current_num, current_title, current_fields, current_extra
        if in_numbered_item and current_title:
            output.append(render_risk_card(current_num, current_title, current_fields, current_extra))
        in_numbered_item = False
        current_num = None
        current_title = None
        current_fields = {}
        current_extra = []

    in_details_block = False
    details_lines = []

    def flush_details(label):
        nonlocal in_details_block, details_lines
        if in_details_block and details_lines:
            body = "".join(f"<p>{safe_inline(l)}</p>" for l in details_lines if l.strip())
            output.append(
                f'<details class="brief-details"><summary>{esc(label)}</summary>'
                f'<div class="brief-details-body">{body}</div></details>'
            )
        in_details_block = False
        details_lines = []

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()

        # Skip metadata header lines
        if line.startswith("Date:") or line.startswith("Tail-Risk Brief v"):
            continue

        # Detect section headers for non-numbered content
        # "Dropped / merged:" / "Underpricing checklist:" / "FINRA short volume" / "Process:"
        stripped = line.strip()

        # Numbered risk item title
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            flush_item()
            in_numbered_item = True
            current_num = m.group(1)
            current_title = m.group(2).strip()
            current_fields = {}
            current_extra = []
            continue

        # If we're inside a numbered item, parse field lines
        if in_numbered_item:
            # Score line
            if re.match(r"\s+Score:", line):
                composite, breakdown = parse_score_line(line)
                current_fields["composite"] = composite
                current_fields["breakdown"] = breakdown
                continue
            # Evidence line
            if re.match(r"\s+Evidence:", line):
                level, sources = parse_evidence_line(line)
                current_fields["evidence_level"] = level
                current_fields["evidence_sources"] = sources
                continue
            # Levers line
            if re.match(r"\s+Levers:", line):
                current_fields["levers"] = parse_levers_line(line)
                continue
            # Disconfirm line
            m_dc = re.match(r"\s+Disconfirm:\s*(.+)", line)
            if m_dc:
                current_fields["disconfirm"] = m_dc.group(1).strip()
                continue
            # If true line
            m_it = re.match(r"\s+If true\s*→\s*(.+)", line)
            if m_it:
                current_fields["if_true"] = m_it.group(1).strip()
                continue
            # Watch line
            m_w = re.match(r"\s+Watch:\s*(.+)", line)
            if m_w:
                current_fields["watch_html"] = render_watch_line(line)
                continue
            # Merged legs line — goes to extra/details
            if re.match(r"\s+Merged legs:", line):
                current_extra.append(line.strip())
                continue
            # Blank line inside item — skip
            if not stripped:
                continue
            # Any other non-blank line inside item before next numbered item
            # could be continuation — put in extra
            current_extra.append(stripped)
            continue

        # Outside numbered items: handle section blocks

        # Blank line
        if not stripped:
            continue

        # Section headers for collapsed details
        if re.match(r"^(Dropped\s*/\s*merged|Underpricing\s+checklist|FINRA\s+short\s+volume|Process)\s*:", stripped, re.I):
            flush_item()
            # Determine label
            label_map = {
                "dropped": "🗑️ Dropped / merged items",
                "underpricing": "📋 Underpricing checklist",
                "finra": "📊 FINRA short volume",
                "process": "⚙️ Process notes",
            }
            label = "Technical details"
            for key, val in label_map.items():
                if key in stripped.lower():
                    label = val
                    break

            # The header line itself may have content after the colon
            colon_content = stripped.split(":", 1)
            if len(colon_content) > 1 and colon_content[1].strip():
                details_lines.append(colon_content[1].strip())

            # Collect lines until next blank-blank or numbered item or EOF
            in_details_block = True
            # We need to consume subsequent lines
            # But since we're in a for loop, we'll set a flag and accumulate
            # Actually, let me use a different approach - collect inline
            continue

        # If we're in a details block, accumulate lines
        if in_details_block:
            # Check if this line starts a new section or numbered item
            if re.match(r"^\d+\.\s+", line) or re.match(r"^(Dropped|Underpricing|FINRA|Process)\s*[:/]", stripped, re.I):
                flush_details("Technical details")
                # Re-process this line
                # It's a new section or numbered item
                if re.match(r"^\d+\.\s+", line):
                    in_numbered_item = True
                    m_num = re.match(r"^(\d+)\.\s+(.+)", line)
                    current_num = m_num.group(1)
                    current_title = m_num.group(2).strip()
                    current_fields = {}
                    current_extra = []
                    continue
                else:
                    # New section header - loop will handle it
                    # Actually we need to handle it here
                    label_map = {
                        "dropped": "🗑️ Dropped / merged items",
                        "underpricing": "📋 Underpricing checklist",
                        "finra": "📊 FINRA short volume",
                        "process": "⚙️ Process notes",
                    }
                    label = "Technical details"
                    for key, val in label_map.items():
                        if key in stripped.lower():
                            label = val
                            break
                    colon_content = stripped.split(":", 1)
                    if len(colon_content) > 1 and colon_content[1].strip():
                        details_lines.append(colon_content[1].strip())
                    in_details_block = True
                    continue

            details_lines.append(stripped)
            continue

        # Bullet items outside numbered items and details blocks
        m_bullet = re.match(r"^[-•]\s+(.+)", stripped)
        if m_bullet:
            # Could be part of a details section that hasn't been started
            # Or standalone bullets - collapse into details
            if not in_details_block:
                in_details_block = True
                details_lines = []
            details_lines.append(stripped)
            continue

        # Other standalone lines
        if stripped:
            if not in_details_block:
                in_details_block = True
                details_lines = []
            details_lines.append(stripped)

    # Flush any remaining content
    flush_item()
    flush_details("Technical details")

    return "\n".join(output)


def format_date_human(date_str):
    """Convert 2026-07-23 to 'July 23, 2026'."""
    try:
        d = dt.datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return d.strftime("%B %-d, %Y")
    except ValueError:
        return date_str


def render_brief_entry(path):
    """Render a single brief .md file as an HTML <article> block."""
    raw = open(path).read()

    # Extract date
    m = re.search(r"^Date:\s*(.+)$", raw, re.M)
    if m:
        brief_date = m.group(1).strip()
    else:
        brief_date = os.path.basename(path).replace(".md", "")

    date_display = format_date_human(brief_date)
    body_html = parse_brief_body(raw)

    return (
        f'                <article class="brief-entry" id="brief-{esc(brief_date)}">\n'
        f'                    <details open>\n'
        f'                        <summary><time datetime="{esc(brief_date)}">{esc(date_display)}</time></summary>\n'
        f'                        <div class="brief-entry-body">\n'
        f'{body_html}\n'
        f'                        </div>\n'
        f'                    </details>\n'
        f'                </article>'
    )


def build_brief_css():
    """Return CSS for brief cards."""
    return """
        .brief-entry-body { padding: 0 0 20px; font-size: 13.5px; line-height: 1.6; color: var(--bl-ink); }
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
        .brief-signals ul { margin: 4px 0 6px; padding-left: 20px; }
        .brief-signals li { margin: 3px 0; font-size: 13px; }
        .brief-details { margin-top: 10px; border-top: 1px dashed var(--bl-divider); padding-top: 8px; }
        .brief-details > summary { cursor: pointer; font-size: 12px; color: var(--bl-faint); list-style: none; }
        .brief-details > summary::before { content: '▸ '; }
        .brief-details[open] > summary::before { content: '▾ '; }
        .brief-details-body { padding: 6px 0; font-size: 12px; color: var(--bl-muted); }
        .brief-details-body p { margin: 3px 0; }
"""


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
    latest_display = format_date_human(latest_date)
    entry_count = len(all_paths)

    panel_lines = [
        '            <section class="trading-panel brief-panel" id="brief-panel" role="tabpanel" tabindex="0" aria-labelledby="brief-tab" hidden>',
        '                <div class="position-head">',
        '                    <h2 id="brief-heading">Morning Brief</h2>',
        f'                    <span>{entry_count} briefs · latest {esc(latest_display)} · pre-market CT</span>',
        '                </div>',
        '                <p class="trading-takeaway">Daily tail-risk research in plain English. Each card breaks down what\'s happening, what could prove it wrong, and what to watch. Newest first.</p>',
        '                <div class="brief-log">',
        entries_html,
        '                </div>',
        '                <p class="trading-note">Research and idea generation only. Not trade recommendations or investment advice.</p>',
        '            </section>',
    ]
    panel = "\n".join(panel_lines)

    page = open(PAGE).read()

    # Ensure tab button exists (after portfolio tab)
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

    # Update brief CSS: replace old brief-entry-body / brief-content CSS with new card CSS
    brief_css = build_brief_css()

    # Remove old brief CSS lines and inject new ones
    # We replace from .brief-entry-body through .brief-content .brief-num block
    old_css_pattern = r"(\.brief-entry-body\s*\{[^}]+\}(?:\s*\n\s*\.brief-entry-body[^}]+\}[^}]*\}?)*)"
    # Actually, let's be more targeted - replace the old CSS block between markers
    # The old CSS spans from line ~175 to ~190. Let's replace specific selectors.

    # Remove old .brief-entry-body and .brief-content style blocks
    old_blocks = [
        # brief-entry-body block (lines 175-182)
        r'\.brief-entry-body\s*\{[^}]+\}\s*\n(\.brief-entry-body[^}]+\}[^}]*\}\s*\n)*',
        # brief-content block (lines 183-190)
        r'\.brief-content\s*\{[^}]+\}\s*\n(\.brief-content[^}]+\}[^}]*\}\s*\n)*',
    ]

    # Simpler: just inject new CSS right before the first old brief CSS line
    # Find the old CSS and replace it
    old_css_regex = re.compile(
        r'\.brief-entry-body\s*\{.*?\.brief-content\s+\.brief-num\s*\{[^}]+\}',
        re.S
    )

    if old_css_regex.search(page):
        page = old_css_regex.sub(brief_css.strip(), page, count=1)
    else:
        # If old CSS not found, inject after .brief-entry summary CSS
        inject_point = ".brief-entry > details > summary time"
        if inject_point in page:
            page = page.replace(
                inject_point + " { font-variant-numeric: tabular-nums; }",
                inject_point + " { font-variant-numeric: tabular-nums; }\n" + brief_css,
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
