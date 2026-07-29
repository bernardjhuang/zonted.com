#!/usr/bin/env python3
"""Render the latest structured Grok Risk journal entry."""
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "grok-risk.json"
PAGE = ROOT / "trading" / "grok-risk" / "index.html"
START = "<!-- AUTO:GROK_RISK:START -->"
END = "<!-- AUTO:GROK_RISK:END -->"


def validate(payload: dict) -> dict:
    if payload.get("schema_version") != 1 or payload.get("model") != "Grok 4.5":
        raise ValueError("grok-risk requires schema 1 and model Grok 4.5")
    entries = payload.get("entries") or []
    if not entries:
        raise ValueError("grok-risk requires at least one entry")
    entry = entries[0]
    if entry.get("model_id") != "grok-4.5" or entry.get("stance") not in {"Risk-on", "Neutral", "Risk-off"}:
        raise ValueError("invalid Grok model metadata or stance")
    rating = entry.get("risk_appetite")
    if not isinstance(rating, (int, float)) or not 0 <= float(rating) <= 10:
        raise ValueError("Grok risk appetite must be between 0 and 10")
    return entry


def render(entry: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    rating = float(entry["risk_appetite"])
    color = {"Risk-on": "#087a42", "Neutral": "#b27b20", "Risk-off": "#b4404b"}[entry["stance"]]
    journal = "".join(f'<p style="font-size:1.05rem;line-height:1.6;margin-bottom:16px;">{esc(value)}</p>' for value in entry["journal"])
    supports = "".join(f"<li>{esc(value)}</li>" for value in entry["what_supports_risk"])
    restraints = "".join(f"<li>{esc(value)}</li>" for value in entry["what_holds_it_back"])
    changes = "".join(f"<li>{esc(value)}</li>" for value in entry["what_changes_my_mind"])
    sources = " · ".join(
        f'<a href="{esc(source["url"])}" rel="noopener">{esc(source["title"])}</a>'
        for source in entry["sources"]
    )
    return f'''<div class="risk-assessment" data-model="Grok 4.5" data-rating="{rating:g}" data-stance="{esc(entry["stance"])}" style="max-width:720px;margin:0 auto;padding:20px 0;">
<h2 style="font-size:1.5rem;margin-bottom:12px;color:{color};">{esc(entry["as_of_date"])} · {esc(entry["stance"])} ({rating:g}/10)</h2>
<p style="font-size:1.05rem;line-height:1.6;margin-bottom:20px;"><strong>{esc(entry["headline"])}</strong></p>
{journal}
<h3 style="margin-top:24px;margin-bottom:8px;">What Supports Risk</h3><ul style="line-height:1.7;margin-bottom:20px;">{supports}</ul>
<h3 style="margin-top:24px;margin-bottom:8px;">What Holds It Back</h3><ul style="line-height:1.7;margin-bottom:20px;">{restraints}</ul>
<h3 style="margin-top:24px;margin-bottom:8px;">What Changes My Mind</h3><ul style="line-height:1.7;margin-bottom:20px;">{changes}</ul>
<details class="trading-method"><summary>Methodology and limitations</summary><p><b>{esc(entry["methodology"]["name"])}</b> — {esc(entry["methodology"]["explanation"])}</p><p>{esc(" · ".join(entry["limitations"]))}</p></details>
<p class="risk-journal-source">Sources: {sources}. This is Grok's model output, not a Zonted mechanical score.</p>
</div>'''


def main() -> int:
    payload = json.loads(DATA.read_text())
    entry = validate(payload)
    page = PAGE.read_text()
    block = f"{START}\n{render(entry)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), block, page, count=1, flags=re.S)
    if updated == page:
        print(f"[grok-risk] already current: {entry['as_of_date']} · {entry['risk_appetite']}/10")
        return 0
    PAGE.write_text(updated)
    print(f"[grok-risk] rendered: {entry['as_of_date']} · {entry['risk_appetite']}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
