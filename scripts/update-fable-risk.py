#!/usr/bin/env python3
"""Append either a mechanical Fable rubric entry or an independent model journal entry."""
import argparse
import html as html_lib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "fable-risk", "index.html")
DATA = os.path.join(ROOT, "trading", "fable-risk.json")
START, END = "<!-- AUTO:FABLE_RISK:START -->", "<!-- AUTO:FABLE_RISK:END -->"
VCLS = {"RISK-ON": "fr-on", "NEUTRAL": "fr-neutral", "RISK-OFF": "fr-off"}
SCLS = {1: ("enter", "+1 on"), 0: ("watch", "0 neutral"), -1: ("short", "−1 off")}
SESSION_RANK = {"pre-market": 0, "intraday": 1, "post-close": 2}


def session_of(entry):
    return entry.get("session", "pre-market")


def rating_of(entry):
    return round((entry["score"] / entry["n_signals"] + 1) * 5, 1)


def render(entry, open_=True):
    rating = rating_of(entry)
    rows = ""
    for signal in entry["signals"]:
        cls, label = SCLS[int(signal["score"])]
        rows += (f'<tr><td>{signal["name"]}<span class="sub">{signal["rule"]}</span></td>'
                 f'<td class="num">{signal["value"]}</td>'
                 f'<td><span class="tag {cls}">{label}</span></td></tr>')
    sources = " · ".join(f'<a href="{item["u"]}" rel="noopener">{item["t"]}</a>' for item in entry["sources"])
    body = f'''<div class="fr-verdict {VCLS[entry["verdict"]]}">
  <div class="fr-call">{entry["verdict"]}</div>
  <div class="fr-sub">{entry["subtitle"]} · signal sum {entry["score"]:+d} of {entry["n_signals"]} · composite {entry["composite"]}</div>
  <div class="fr-rating" title="0 = maximum risk-off · 10 = maximum risk-on">
    <span class="fr-rating-num">{rating:g}</span><span class="fr-rating-scale">/ 10</span>
    <span class="fr-rating-bar"><span class="fr-rating-fill" style="width:{100 - rating * 10:g}%"></span></span>
    <span class="fr-rating-cap">risk appetite</span>
  </div>
</div>
{''.join(entry["narrative"])}
<div class="card"><h2>Signal ledger<span class="card-r">rubric v1 · each −1 / 0 / +1</span></h2>
<div class="tw"><table style="min-width:560px"><thead><tr><th>Signal</th><th class="num">Reading</th><th>Score</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
<div class="card"><h2>What flips this call</h2>
<div class="mkt"><span class="lbl"><b>To risk-off:</b> {entry["flips"]["to_off"]}</span></div>
<div class="mkt"><span class="lbl"><b>To risk-on:</b> {entry["flips"]["to_on"]}</span></div></div>
<p class="footnote">Sources: {sources}</p>'''
    return (f'<details class="fr-entry"{" open" if open_ else ""}>'
            f'<summary><time datetime="{entry["date"]}">{entry["date"]}</time>'
            f'<span class="fr-sumverdict {VCLS[entry["verdict"]]}">{entry["verdict"]}</span>'
            f'<span class="fr-sumsession">{session_of(entry)}</span><span class="fr-sumfor">assessment for {entry["assess_for"]}</span><span class="fr-sumrating">{rating:g}/10</span></summary>'
            f'<div class="fr-body">{body}</div></details>')


def render_model_entry(entry, open_=True):
    esc = lambda value: html_lib.escape(str(value), quote=True)
    stance = entry["stance"]
    verdict = stance.upper()
    cls = {"Risk-on": "fr-on", "Neutral": "fr-neutral", "Risk-off": "fr-off"}[stance]
    rating = float(entry["risk_appetite"])
    paragraphs = "".join(f"<p>{esc(value)}</p>" for value in entry["journal"])
    supports = "".join(f"<li>{esc(value)}</li>" for value in entry["what_supports_risk"])
    restraints = "".join(f"<li>{esc(value)}</li>" for value in entry["what_holds_it_back"])
    changes = "".join(f"<li>{esc(value)}</li>" for value in entry["what_changes_my_mind"])
    sources = " · ".join(
        f'<a href="{esc(source["url"])}" rel="noopener">{esc(source["title"])}</a>'
        for source in entry["sources"]
    )
    body = f'''<div class="fr-verdict {cls}">
  <div class="fr-call">{esc(verdict)}</div>
  <div class="fr-sub">independent model-selected methodology · {esc(entry["confidence"])} confidence</div>
  <div class="fr-rating" title="0 = maximum risk-off · 10 = maximum risk-on">
    <span class="fr-rating-num">{rating:g}</span><span class="fr-rating-scale">/ 10</span>
    <span class="fr-rating-bar"><span class="fr-rating-fill" style="width:{100 - rating * 10:g}%"></span></span>
    <span class="fr-rating-cap">risk appetite</span>
  </div>
</div>
<h2>{esc(entry["headline"])}</h2>{paragraphs}
<div class="card"><h2>What supports risk</h2><ul>{supports}</ul></div>
<div class="card"><h2>What holds it back</h2><ul>{restraints}</ul></div>
<div class="card"><h2>What changes this call</h2><ul>{changes}</ul></div>
<details class="trading-method"><summary>Methodology and limitations</summary><p><b>{esc(entry["methodology"]["name"])}</b> — {esc(entry["methodology"]["explanation"])}</p><p>{esc(" · ".join(entry["limitations"]))}</p></details>
<p class="footnote">Sources: {sources}</p>'''
    return (f'<details class="fr-entry fr-model-entry"{" open" if open_ else ""}>'
            f'<summary><time datetime="{esc(entry["as_of_date"])}">{esc(entry["as_of_date"])}</time>'
            f'<span class="fr-sumverdict {cls}">{esc(verdict)}</span>'
            f'<span class="fr-sumsession">{esc(entry["session"])} · journal</span>'
            f'<span class="fr-sumfor">independent Claude Fable 5 journal</span>'
            f'<span class="fr-sumrating">{rating:g}/10</span></summary>'
            f'<div class="fr-body">{body}</div></details>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry")
    args = parser.parse_args()
    entry = json.load(open(args.entry))
    data = {"schema_version": 1, "entries": [], "model_entries": []}
    if os.path.exists(DATA):
        data = json.load(open(DATA))
        data.setdefault("model_entries", [])
    if entry.get("prompt_version") == "zonted-independent-risk-v1":
        data["model_entries"] = [existing for existing in data["model_entries"]
                                 if (existing["as_of_date"], existing["session"]) != (entry["as_of_date"], entry["session"])]
        data["model_entries"].insert(0, entry)
    else:
        entry["rating"] = rating_of(entry)
        entry["session"] = session_of(entry)
        data["entries"] = [existing for existing in data["entries"]
                           if (existing["date"], session_of(existing)) != (entry["date"], entry["session"])]
        data["entries"].insert(0, entry)
    with open(DATA, "w") as handle:
        json.dump(data, handle, indent=1)
        handle.write("\n")

    page = open(PAGE).read()
    start, end = page.index(START) + len(START), page.index(END)
    combined = [(item.get("date") or item["as_of_date"], SESSION_RANK.get(session_of(item), 1), renderer, item)
                for items, renderer in ((data["entries"], render), (data["model_entries"], render_model_entry))
                for item in items]
    combined.sort(key=lambda row: row[:2], reverse=True)
    rendered = [renderer(item, index == 0) for index, (_, _, renderer, item) in enumerate(combined)]
    block = "\n" + "\n".join(rendered) + "\n"
    open(PAGE, "w").write(page[:start] + block + page[end:])
    if entry.get("prompt_version"):
        print(f"fable-risk: {entry['as_of_date']} {entry['stance']} ({entry['risk_appetite']}/10) · independent model journal")
    else:
        print(f"fable-risk: {entry['date']} {entry['verdict']} ({entry['composite']}) · {len(data['entries'])} mechanical entries")


if __name__ == "__main__":
    main()
