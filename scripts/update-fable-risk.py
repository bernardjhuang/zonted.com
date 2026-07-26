#!/usr/bin/env python3
"""Append a Fable Risk daily entry.

Reads an entry JSON (argv[1]), prepends it into the AUTO:FABLE_RISK block of
trading/fable-risk/index.html (newest entry expanded, older ones collapsed),
and appends it to trading/fable-risk.json.

Entry schema:
{
  "date": "2026-07-25", "assess_for": "Mon Jul 27 open",
  "verdict": "NEUTRAL", "subtitle": "calm gauges, defensive internals",
  "score": 1, "n_signals": 11, "composite": "+0.09",
  "signals": [{"name","value","rule","score"}],          # score in -1/0/+1
  "narrative": ["<p>…</p>", …],                            # html paragraphs
  "flips": {"to_off": "…", "to_on": "…"},
  "sources": [{"t": "title", "u": "url"}]
}
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "fable-risk", "index.html")
DATA = os.path.join(ROOT, "trading", "fable-risk.json")
START, END = "<!-- AUTO:FABLE_RISK:START -->", "<!-- AUTO:FABLE_RISK:END -->"
VCLS = {"RISK-ON": "fr-on", "NEUTRAL": "fr-neutral", "RISK-OFF": "fr-off"}
SCLS = {1: ("enter", "+1 on"), 0: ("watch", "0 neutral"), -1: ("short", "−1 off")}


def render(entry, open_=True):
    rows = ""
    for s in entry["signals"]:
        cls, label = SCLS[int(s["score"])]
        rows += (f'<tr><td>{s["name"]}<span class="sub">{s["rule"]}</span></td>'
                 f'<td class="num">{s["value"]}</td>'
                 f'<td><span class="tag {cls}">{label}</span></td></tr>')
    src = " · ".join(f'<a href="{x["u"]}" rel="noopener">{x["t"]}</a>' for x in entry["sources"])
    body = f"""
<div class="fr-verdict {VCLS[entry["verdict"]]}">
  <div class="fr-call">{entry["verdict"]}</div>
  <div class="fr-sub">{entry["subtitle"]} · signal sum {entry["score"]:+d} of {entry["n_signals"]} · composite {entry["composite"]}</div>
</div>
{''.join(entry["narrative"])}
<div class="card"><h2>Signal ledger<span class="card-r">rubric v1 · each −1 / 0 / +1</span></h2>
<div class="tw"><table style="min-width:560px"><thead><tr><th>Signal</th><th class="num">Reading</th><th>Score</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
<div class="card"><h2>What flips this call</h2>
<div class="mkt"><span class="lbl"><b>To risk-off:</b> {entry["flips"]["to_off"]}</span></div>
<div class="mkt"><span class="lbl"><b>To risk-on:</b> {entry["flips"]["to_on"]}</span></div></div>
<p class="footnote">Sources: {src}</p>
"""
    return (f'<details class="fr-entry"{" open" if open_ else ""}>'
            f'<summary><time datetime="{entry["date"]}">{entry["date"]}</time>'
            f'<span class="fr-sumverdict {VCLS[entry["verdict"]]}">{entry["verdict"]}</span>'
            f'<span class="fr-sumfor">assessment for {entry["assess_for"]}</span></summary>'
            f'<div class="fr-body">{body}</div></details>')


def main():
    entry = json.load(open(sys.argv[1]))
    data = {"schema_version": 1, "entries": []}
    if os.path.exists(DATA):
        data = json.load(open(DATA))
    data["entries"] = [e for e in data["entries"] if e["date"] != entry["date"]]
    data["entries"].insert(0, entry)
    json.dump(data, open(DATA, "w"), indent=1)

    page = open(PAGE).read()
    a, b = page.index(START) + len(START), page.index(END)
    html = "\n" + "\n".join(render(e, i == 0) for i, e in enumerate(data["entries"])) + "\n"
    open(PAGE, "w").write(page[:a] + html + page[b:])
    print(f"fable-risk: {entry['date']} {entry['verdict']} ({entry['composite']}) · {len(data['entries'])} entries")


if __name__ == "__main__":
    main()
