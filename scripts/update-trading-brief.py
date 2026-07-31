#!/usr/bin/env python3
"""Copy the latest tail-risk brief into the trading site data directory."""
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEFS_DIR = Path("/Users/psy/.openclaw/workspace/tail-risk-scanner/briefs")
OUT = ROOT / "trading" / "brief.json"

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    brief_path = BRIEFS_DIR / f"{today}.md"
    if not brief_path.exists():
        # Try most recent
        briefs = sorted(BRIEFS_DIR.glob("*.md"))
        if not briefs:
            print("No brief found", file=sys.stderr)
            sys.exit(1)
        brief_path = briefs[-1]
        today = brief_path.stem

    markdown = brief_path.read_text()
    # Split into sections for rendering
    sections = re.split(r'^# ', markdown, flags=re.MULTILINE)
    title = ""
    body_sections = []
    for i, s in enumerate(sections):
        s = s.strip()
        if not s:
            continue
        first_line = s.split('\n')[0]
        body = '\n'.join(s.split('\n')[1:]).strip()
        if i == 0:
            title = s.strip()
        else:
            body_sections.append({"title": first_line, "body": body})

    data = {
        "date": today,
        "updated": datetime.now().isoformat(),
        "markdown": markdown,
        "sections": body_sections,
    }
    OUT.write_text(json.dumps(data, indent=2))
    print(f"Wrote {OUT} ({len(markdown)} chars, date={today})")

if __name__ == "__main__":
    main()
