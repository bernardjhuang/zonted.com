#!/usr/bin/env python3
"""Validate and render the privacy-safe autonomous paper-trading journal."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "autonomous.json"
PAGE = ROOT / "trading" / "autonomous" / "index.html"
START = "<!-- AUTO:AUTONOMOUS_JOURNAL:START -->"
END = "<!-- AUTO:AUTONOMOUS_JOURNAL:END -->"
FORBIDDEN_KEYS = {
    "quantity",
    "qty",
    "shares",
    "contracts",
    "entry_price",
    "execution_price",
    "fill_price",
    "stop_price",
    "target_price",
    "position_return_pct",
    "open_r_multiple",
    "notional",
    "dollar_pnl",
    "balance",
    "buying_power",
    "net_liquidation_value",
    "nlv",
    "account_id",
    "account_number",
    "order_id",
    "client_order_id",
}
REQUIRED_ENTRY_KEYS = {
    "id",
    "published_at",
    "session",
    "mode",
    "decision",
    "risk_appetite",
    "headline",
    "thoughts",
    "strategies",
    "positions",
    "pnl",
    "candidate_review",
    "review_summary",
    "denominators",
    "limitations",
    "source_receipts",
}
PNL_KEYS = {
    "realized_pct_of_virtual_basis",
    "unrealized_pct_of_virtual_basis",
    "marked_total_pct_of_virtual_basis",
    "closed_trades",
    "note",
}
POSITION_KEYS = {
    "symbol",
    "direction",
    "status",
    "thesis",
    "risk",
    "return_since_entry_pct",
    "unrealized_pnl_pct_of_virtual_basis",
}
BAND_PCT = re.compile(r"^(?:between|less than|more than|at least|at most|approximately) .+%$", re.I)
PILOT_START_DATE = "2026-08-10"
PILOT_STRATEGIES = {
    "Day-two post-gap consolidation",
    "Negative-catalyst oversold reclaim",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def walk(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_KEYS:
                raise ValueError(f"privacy-forbidden key at {path}.{key}")
            walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if "$" in value:
            raise ValueError(f"dollar-denominated text at {path}")
        if re.search(r"\b(?:account|order)[ _-]?(?:id|number)\b", value, re.I):
            raise ValueError(f"identifier-like text at {path}")


def validate_public_pct(value: object, field: str) -> None:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric or a coarse percentage band")
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str) and BAND_PCT.fullmatch(value):
        return
    raise ValueError(f"{field} must be numeric or a coarse percentage band")


def reviewed_content_sha256(entry: dict) -> str:
    reviewed = copy.deepcopy(entry)
    reviewed.pop("review_summary", None)
    payload = {"schema_version": 1, "entries": [reviewed]}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate(payload: dict) -> list[dict]:
    if payload.get("schema_version") != 1:
        raise ValueError("autonomous journal requires schema_version 1")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("autonomous journal requires at least one entry")
    if len({entry.get("id") for entry in entries}) != len(entries):
        raise ValueError("autonomous journal entry IDs must be unique")
    stamps = [str(entry.get("published_at", "")) for entry in entries]
    if stamps != sorted(stamps, reverse=True):
        raise ValueError("autonomous journal entries must be newest first")
    walk(payload)
    for entry in entries:
        missing = REQUIRED_ENTRY_KEYS - set(entry)
        if missing:
            raise ValueError(f"{entry.get('id')} missing keys: {sorted(missing)}")
        if entry["mode"] != "paper":
            raise ValueError("Autonomous public journal is paper-only")
        if entry["decision"] not in {"TRADE", "NO_TRADE", "HOLD", "REVIEW"}:
            raise ValueError("invalid autonomous decision")
        appetite = entry["risk_appetite"]
        if isinstance(appetite, bool) or not isinstance(appetite, (int, float)) or not 0 <= appetite <= 10:
            raise ValueError("risk_appetite must be between 0 and 10")
        if set(entry["pnl"]) != PNL_KEYS:
            raise ValueError("public P&L must use the exact percentage-only schema")
        for key in PNL_KEYS - {"note", "closed_trades"}:
            validate_public_pct(entry["pnl"][key], key)
        for position in entry["positions"]:
            if set(position) != POSITION_KEYS:
                raise ValueError("position schema must stay quantity- and price-free")
            validate_public_pct(position["return_since_entry_pct"], "return_since_entry_pct")
            validate_public_pct(
                position["unrealized_pnl_pct_of_virtual_basis"],
                "unrealized_pnl_pct_of_virtual_basis",
            )
        reviews = entry["review_summary"]
        if reviews.get("public_entry_status") != "PASS":
            raise ValueError("public entry requires dual-review PASS")
        approved = {(row.get("model"), row.get("verdict")) for row in reviews.get("public_entry_reviews", [])}
        if not any("Fable" in str(model) and verdict == "PASS" for model, verdict in approved):
            raise ValueError("public entry requires Fable PASS")
        if not any("Grok 4.5" in str(model) and verdict == "PASS" for model, verdict in approved):
            raise ValueError("public entry requires Grok 4.5 PASS")
        expected_content_hash = reviews.get("reviewed_content_sha256")
        if expected_content_hash:
            if expected_content_hash != reviewed_content_sha256(entry):
                raise ValueError("public entry changed after dual review")
            for review in reviews.get("public_entry_reviews", []):
                receipt_path = str(review.get("receipt_path", ""))
                receipt_sha256 = str(review.get("receipt_sha256", ""))
                if not receipt_path.startswith("/trading/autonomous-reviews/"):
                    raise ValueError("review receipt path must stay under autonomous-reviews")
                receipt_file = ROOT / receipt_path.lstrip("/")
                if not receipt_file.is_file():
                    raise ValueError(f"missing review receipt: {receipt_path}")
                raw = receipt_file.read_bytes()
                if hashlib.sha256(raw).hexdigest() != receipt_sha256:
                    raise ValueError(f"review receipt hash mismatch: {receipt_path}")
                receipt = json.loads(raw)
                if receipt.get("exact_public_entry_sha256") != expected_content_hash:
                    raise ValueError(f"review receipt is bound to different content: {receipt_path}")
                if (receipt.get("result") or {}).get("verdict") != "PASS":
                    raise ValueError(f"review receipt is not PASS: {receipt_path}")
    return entries


def pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def pct_label(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return pct(float(value))
    raise ValueError("percentage display value is invalid")


def bullets(values: list[str], css: str = "") -> str:
    klass = f' class="{css}"' if css else ""
    return f"<ul{klass}>" + "".join(f"<li>{esc(value)}</li>" for value in values) + "</ul>"


def public_strategy_status(entry: dict, row: dict) -> tuple[str, bool]:
    """Correct premature pilot labels without mutating the append-only source entry."""
    needs_erratum = (
        str(entry["published_at"])[:10] < PILOT_START_DATE
        and row["name"] in PILOT_STRATEGIES
        and row["status"] == "executable at standard size"
    )
    if needs_erratum:
        return "scheduled for the 2026-08-10 paper pilot at standard size", True
    return str(row["status"]), False


def render_entry(entry: dict, latest: bool) -> str:
    pnl = entry["pnl"]
    pnl_cards = "".join(
        f'<div class="autonomous-metric"><span>{label}</span><strong class="{("up" if isinstance(value, (int, float)) and value > 0 else "down" if isinstance(value, (int, float)) and value < 0 else "")}">{esc(pct_label(value))}</strong></div>'
        for label, value in (
            ("Realized", pnl["realized_pct_of_virtual_basis"]),
            ("Unrealized", pnl["unrealized_pct_of_virtual_basis"]),
            ("Marked total", pnl["marked_total_pct_of_virtual_basis"]),
        )
    )
    positions = "".join(
        f'''<article class="autonomous-position">
        <header><div><span>{esc(row["direction"])}</span><h3>{esc(row["symbol"])}</h3></div><strong>{esc(row["status"])}</strong></header>
        <p>{esc(row["thesis"])}</p><p class="autonomous-risk"><b>Risk:</b> {esc(row["risk"])}</p>
        <div class="autonomous-position-pnl"><span>Position return since entry <b>{esc(pct_label(row["return_since_entry_pct"]))}</b></span><span>Contribution to virtual basis <b>{esc(pct_label(row["unrealized_pnl_pct_of_virtual_basis"]))}</b></span></div>
        </article>'''
        for row in entry["positions"]
    ) or '<p class="autonomous-empty">No open positions.</p>'
    strategy_rows = [(row, *public_strategy_status(entry, row)) for row in entry["strategies"]]
    strategies = "".join(
        f'<article><span>{esc(status)}</span><h3>{esc(row["name"])}</h3><p>{esc(row["rules"])}</p></article>'
        for row, status, _ in strategy_rows
    )
    strategy_erratum = (
        '<p class="autonomous-note"><b>Public erratum:</b> this archived entry originally labeled two aggressive lanes executable. Their reviewed paper pilot does not begin until 2026-08-10; the corrected public labels appear above without rewriting the append-only source entry.</p>'
        if any(corrected for _, _, corrected in strategy_rows)
        else ""
    )
    candidates = "".join(
        f'<tr><th scope="row">{esc(row["symbol"])}</th><td><b>{esc(row["disposition"])}</b></td><td>{esc(row["reason"])}</td></tr>'
        for row in entry["candidate_review"]
    )
    approvals = "".join(
        f'<article><span>{esc(row["verdict"])}</span><h3>{esc(row["model"])}</h3><p>{esc(row["result"])}</p>'
        + (f'<a href="{esc(row["receipt_path"])}">Full dual-track receipt</a>' if row.get("receipt_path") else "")
        + "</article>"
        for row in entry["review_summary"]["public_entry_reviews"]
    )
    receipts = " · ".join(f"{esc(key)} <code>{esc(value[:12])}…</code>" for key, value in entry["source_receipts"].items())
    label = "Latest entry" if latest else "Archived entry"
    return f'''<article class="autonomous-entry" id="entry-{esc(entry["id"])}" data-decision="{esc(entry["decision"])}">
      <header class="autonomous-entry-head"><div><span>{label} · {esc(entry["session"])} · PAPER ONLY</span><h2>{esc(entry["published_at"][:10])} · {esc(entry["decision"])}</h2></div><div class="autonomous-risk-score"><span>Risk appetite</span><strong>{float(entry["risk_appetite"]):g}/10</strong></div></header>
      <p class="autonomous-headline">{esc(entry["headline"])}</p>
      <section aria-labelledby="thoughts-{esc(entry["id"])}"><h3 id="thoughts-{esc(entry["id"])}">What I thought</h3>{bullets(entry["thoughts"], "autonomous-thoughts")}</section>
      <section aria-labelledby="pnl-{esc(entry["id"])}"><div class="autonomous-section-head"><h3 id="pnl-{esc(entry["id"])}">P&amp;L</h3><span>percentage of private virtual basis</span></div><div class="autonomous-metrics">{pnl_cards}</div><p class="autonomous-note">{esc(pnl["note"])} · {int(pnl["closed_trades"])} closed trade.</p></section>
      <section aria-labelledby="positions-{esc(entry["id"])}"><h3 id="positions-{esc(entry["id"])}">Positions</h3><div class="autonomous-positions">{positions}</div></section>
      <section aria-labelledby="strategies-{esc(entry["id"])}"><h3 id="strategies-{esc(entry["id"])}">Execution lanes considered in this decision</h3><div class="autonomous-grid">{strategies}</div>{strategy_erratum}</section>
      <section aria-labelledby="candidates-{esc(entry["id"])}"><h3 id="candidates-{esc(entry["id"])}">What I passed on</h3><div class="tw"><table class="autonomous-table"><thead><tr><th>Symbol</th><th>Decision</th><th>Reason</th></tr></thead><tbody>{candidates}</tbody></table></div></section>
      <section aria-labelledby="reviews-{esc(entry["id"])}"><div class="autonomous-section-head"><h3 id="reviews-{esc(entry["id"])}">Publication review</h3><span>dual publication review · PASS</span></div><p class="autonomous-note">This PASS means the entry is privacy-safe and statistically honest enough to publish. It is not a strategy verdict or evidence of edge.</p><div class="autonomous-reviews">{approvals}</div>{bullets(entry["review_summary"]["changes_after_grok"], "autonomous-changes")}</section>
      <details class="trading-method"><summary>Denominators, limitations, and receipts</summary><p><b>Triggered/filled bracket outcomes:</b> {esc(entry["denominators"]["triggered_or_filled_bracket_outcomes"])}. Executable, shadow, pre-trigger, and capability-blocked outcomes remain separate.</p>{bullets(entry["limitations"])}<p class="autonomous-receipts">{receipts}</p></details>
    </article>'''


def render(entries: list[dict]) -> str:
    rendered = "\n".join(render_entry(entry, index == 0) for index, entry in enumerate(entries))
    return f'''{START}
<div class="autonomous-journal" data-entry-count="{len(entries)}">
{rendered}
</div>
{END}'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    entries = validate(json.loads(DATA.read_text()))
    page = PAGE.read_text()
    block = render(entries)
    updated, count = re.subn(re.escape(START) + r".*?" + re.escape(END), block, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("autonomous journal render markers are missing")
    if args.check:
        if updated != page:
            raise SystemExit("autonomous journal page is stale; run scripts/update-autonomous-journal.py")
        print(f"[autonomous] check OK · {len(entries)} privacy-safe dual-reviewed entries")
        return 0
    PAGE.write_text(updated)
    print(f"[autonomous] rendered {len(entries)} entries · newest {entries[0]['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
