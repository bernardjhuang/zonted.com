#!/usr/bin/env python3
"""Nightly updater for https://zonted.com/metrics/.

Refreshes the public GA4 + Search Console portfolio cards, commits and pushes
changes, waits briefly for Cloudflare Pages deploy, then posts a Slack update.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
METRICS_HTML = ROOT / "metrics" / "index.html"
FETCHER = ROOT / "scripts" / "fetch-ga4-portfolio.js"
STATE_PATH = Path("/Users/psy/.openclaw/workspace/state/zonted-metrics-cron.json")
LOG_DIR = Path("/Users/psy/.openclaw/workspace/logs")
CHANNEL = "C0APKM06YTC"
THRESHOLD = 0.25
YOUTUBE_SHORTS_URL = "https://www.youtube.com/@tabijiai/shorts"
TABIJI_PUBLISH_LOG = Path("/Users/psy/.openclaw/workspace/tabiji/functions/publish-log.json")
STRIPE_KEYCHAIN_SERVICE = "veracityapi-stripe-readonly-key"
STRIPE_API_VERSION = "2025-10-29.clover"
REVENUE_PERIOD_LABEL = "May 2026"
REVENUE_PERIOD_START = datetime(2026, 5, 1, tzinfo=timezone.utc)
REVENUE_PERIOD_END = datetime(2026, 6, 1, tzinfo=timezone.utc)
MANUAL_REVENUE_CARDS = [
    {
        "key": "tabiji",
        "name": "Tabiji",
        "domain": "tabiji.ai",
        "color": "#2a7a2a",
        "total": "$123.68",
        "label": "estimated royalties",
        "source": "KDP dashboard",
        "rows": [
            {"label": "eBook royalties", "value": "$60.32"},
            {"label": "Print royalties", "value": "$28.82"},
            {"label": "KENP royalties", "value": "$7.90"},
        ],
    },
    {
        "key": "agenttune",
        "name": "AgentTune",
        "domain": "agent-tune.com",
        "color": "#6366f1",
        "total": "$0",
        "label": "current revenue",
        "source": "Open library",
        "rows": [
            {"label": "Status", "value": "Live"},
            {"label": "Model", "value": "Custom tunings"},
        ],
    },
    {
        "key": "zonted",
        "name": "Zonted",
        "domain": "zonted.com",
        "color": "#6f4aa8",
        "total": "$200",
        "label": "May affiliate earnings",
        "source": "WaveSpeedAI affiliate",
        "rows": [
            {"label": "Month", "value": "May 2026"},
            {"label": "Total clicks", "value": "5"},
        ],
    },
]

PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
USER_HOME = "/Users/psy"
ENV = {
    **os.environ,
    "HOME": os.environ.get("HOME") or USER_HOME,
    "USER": os.environ.get("USER") or "psy",
    "LOGNAME": os.environ.get("LOGNAME") or "psy",
    "PATH": PATH,
    "GIT_TERMINAL_PROMPT": "0",
}
MAX_ERROR_OUTPUT = 4000


def redact(text: str) -> str:
    text = re.sub(r"gh[opsu]_[A-Za-z0-9_]+", "gh*_REDACTED", text or "")
    text = re.sub(r"(https://)([^/@\s:]+):([^/@\s]+)@", r"\1\2:REDACTED@", text)
    return text


def run(cmd: list[str], *, cwd: Path = ROOT, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=str(cwd), env=ENV, text=True, capture_output=capture, check=False)
    if check and proc.returncode:
        parts = [f"Command {cmd!r} returned non-zero exit status {proc.returncode}."]
        if proc.stdout:
            parts.append("stdout:\n" + redact(proc.stdout[-MAX_ERROR_OUTPUT:].strip()))
        if proc.stderr:
            parts.append("stderr:\n" + redact(proc.stderr[-MAX_ERROR_OUTPUT:].strip()))
        raise RuntimeError("\n".join(parts))
    return proc


def run_with_retry(cmd: list[str], *, attempts: int = 2, delay: int = 10, **kwargs) -> subprocess.CompletedProcess:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return run(cmd, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def ensure_git_push_auth() -> None:
    """Make GitHub HTTPS auth deterministic before creating a nightly commit.

    The system crontab runs outside an interactive shell, so relying on whatever
    credential helper happens to be initialized can leave a local commit stranded.
    Re-apply GitHub CLI's git credential helper when available, then require a
    non-interactive dry-run push to pass before the updater mutates files.
    """
    gh = shutil.which("gh", path=PATH)
    if gh:
        status = run([gh, "auth", "status", "--hostname", "github.com"], check=False, capture=True)
        if status.returncode == 0:
            run([gh, "auth", "setup-git", "--hostname", "github.com"], check=False, capture=True)

    preflight = run(["git", "push", "--dry-run", "origin", "main"], check=False, capture=True)
    if preflight.returncode == 0:
        return

    # One more setup attempt, in case global git config was rewritten since the
    # first check or gh returned a transient keyring error.
    if gh:
        run([gh, "auth", "setup-git", "--hostname", "github.com"], check=False, capture=True)
        preflight = run(["git", "push", "--dry-run", "origin", "main"], check=False, capture=True)
        if preflight.returncode == 0:
            return

    details = []
    if preflight.stdout:
        details.append("stdout:\n" + redact(preflight.stdout[-MAX_ERROR_OUTPUT:].strip()))
    if preflight.stderr:
        details.append("stderr:\n" + redact(preflight.stderr[-MAX_ERROR_OUTPUT:].strip()))
    suffix = "\n" + "\n".join(details) if details else ""
    raise RuntimeError("GitHub push auth preflight failed; refusing to create a stranded nightly commit." + suffix)


def fmt(n: float) -> str:
    return f"{int(round(n)):,}"


def duration(seconds: float) -> str:
    sec = int(round(seconds))
    return f"{sec // 60}m {sec % 60:02d}s" if sec >= 60 else f"{sec}s"


def pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def compact(n: float) -> str:
    n = float(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return fmt(n)


def money(cents: float, currency: str = "usd") -> str:
    amount = float(cents or 0) / 100
    symbol = "$" if (currency or "usd").lower() == "usd" else f"{currency.upper()} "
    if abs(amount) >= 1_000_000:
        return f"{symbol}{amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"{symbol}{amount:,.0f}"
    if amount.is_integer():
        return f"{symbol}{amount:,.0f}"
    return f"{symbol}{amount:,.2f}"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def title_for_url(url: str) -> str:
    if url.rstrip("/") == "https://tabiji.ai":
        return "tabiji.ai"
    parts = [part for part in url.rstrip("/").split("/") if part]
    if not parts:
        return url
    slug = parts[-1]
    if len(parts) >= 3 and parts[-2] == "scams":
        return slug.replace("-", " ").title() + " Scams"
    return slug.replace("-", " ").title()


def youtube_video_id(url: str) -> str:
    match = re.search(r"(?:shorts/|watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url or "")
    return match.group(1) if match else ""


def date_label(iso_date: str) -> str:
    try:
        parsed = datetime.strptime(iso_date, "%Y-%m-%d")
        return f"{parsed.strftime('%b')} {parsed.day}"
    except ValueError:
        return iso_date


def top_items(items: list[dict]) -> str:
    rows = []
    for idx, item in enumerate(items, 1):
        rows.append(
            f'''                <li class="top-item">
                    <span class="top-rank">{idx}</span>
                    <div class="top-info">
                        <div class="top-title"><a href="{esc(item['url'])}">{esc(item['title'])}</a></div>
                        <div class="top-stats">{item['stats']}</div>
                    </div>
                </li>'''
        )
    return "\n".join(rows)


def fetch_youtube_metrics() -> dict:
    """Fetch current public YouTube Shorts metrics via yt-dlp.

    YouTube Analytics OAuth is still upload-only, so this keeps the public card fresh
    from the channel page until the token is expanded to yt-analytics.readonly.
    """
    ytdlp = shutil.which("yt-dlp", path=PATH)
    if not ytdlp:
        raise RuntimeError("yt-dlp not found; cannot refresh YouTube public metrics")
    proc = run([ytdlp, "--flat-playlist", "--dump-single-json", YOUTUBE_SHORTS_URL], capture=True)
    payload = json.loads(proc.stdout)
    videos = []
    for idx, entry in enumerate(payload.get("entries") or [], 1):
        video_id = entry.get("id")
        if not video_id:
            continue
        url = entry.get("url") or f"https://www.youtube.com/shorts/{video_id}"
        views = int(entry.get("view_count") or 0)
        videos.append(
            {
                "rank": idx,
                "videoId": video_id,
                "title": entry.get("title") or video_id,
                "url": url,
                "views": views,
            }
        )

    top = sorted(videos, key=lambda row: row["views"], reverse=True)[:5]
    publish_dates: dict[str, str] = {}
    if TABIJI_PUBLISH_LOG.exists():
        for row in json.loads(TABIJI_PUBLISH_LOG.read_text()):
            video_id = youtube_video_id(row.get("platforms", {}).get("yt", ""))
            if not video_id:
                continue
            publish_dates[video_id] = datetime.fromtimestamp(int(row.get("ts") or 0)).strftime("%Y-%m-%d")

    views_by_date: dict[str, int] = defaultdict(int)
    tracked_videos = 0
    tracked_views = 0
    for video in videos:
        published = publish_dates.get(video["videoId"])
        if not published:
            continue
        tracked_videos += 1
        tracked_views += video["views"]
        views_by_date[published] += video["views"]

    active_dates = sorted(views_by_date)
    dates: list[str] = []
    if active_dates:
        cursor = datetime.strptime(active_dates[0], "%Y-%m-%d")
        end = datetime.strptime(active_dates[-1], "%Y-%m-%d")
        while cursor <= end:
            dates.append(cursor.strftime("%Y-%m-%d"))
            cursor += timedelta(days=1)
    return {
        "handle": payload.get("uploader_id") or "@tabijiai",
        "subscribers": int(payload.get("channel_follower_count") or 0),
        "videos": len(videos),
        "totalViews": sum(row["views"] for row in videos),
        "topShorts": top,
        "trackedVideos": tracked_videos,
        "trackedViews": tracked_views,
        "timeSeries": {
            "label": "Views by publish date",
            "range": f"{date_label(dates[0])}–{date_label(dates[-1])}" if dates else "",
            "labels": [date_label(day) for day in dates],
            "series": [views_by_date[day] for day in dates],
        },
    }


def keychain_secret(service: str) -> str:
    proc = run(["security", "find-generic-password", "-s", service, "-w"], check=False, capture=True)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    if proc.stderr.strip():
        print(f"⚠️ Keychain lookup failed for {service}: {proc.stderr.strip()}", file=sys.stderr)
    elif proc.returncode:
        print(f"⚠️ Keychain lookup failed for {service}: security exited {proc.returncode}", file=sys.stderr)
    return ""


def stripe_get(path: str, params: dict[str, object] | None = None) -> dict:
    key = os.environ.get("STRIPE_VERACITYAPI_READONLY_KEY") or keychain_secret(STRIPE_KEYCHAIN_SERVICE)
    if not key:
        raise RuntimeError(f"Missing Stripe key: set STRIPE_VERACITYAPI_READONLY_KEY or keychain service {STRIPE_KEYCHAIN_SERVICE}")
    query = parse.urlencode(params or {}, doseq=True)
    url = f"https://api.stripe.com/v1/{path.lstrip('/')}"
    if query:
        url += f"?{query}"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Stripe-Version": STRIPE_API_VERSION,
        },
    )
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def stripe_list(path: str, params: dict[str, object] | None = None) -> list[dict]:
    rows: list[dict] = []
    cursor: str | None = None
    while True:
        request_params = {**(params or {}), "limit": 100}
        if cursor:
            request_params["starting_after"] = cursor
        payload = stripe_get(path, request_params)
        batch = payload.get("data") or []
        rows.extend(batch)
        if not payload.get("has_more") or not batch:
            return rows
        cursor = batch[-1].get("id")


def fetch_stripe_usage_revenue() -> dict:
    """Fetch one-time / usage payments for VeracityAPI.

    VeracityAPI currently charges metered request top-ups rather than Stripe
    subscriptions, so revenue comes from successful charges/payment intents.
    """
    period_start_ts = int(REVENUE_PERIOD_START.timestamp())
    period_end_ts = int(REVENUE_PERIOD_END.timestamp())
    charges = stripe_list("charges")
    balance_transactions = stripe_list("balance_transactions")

    successful = [
        charge
        for charge in charges
        if charge.get("status") == "succeeded" and charge.get("paid") and not charge.get("refunded")
    ]
    period_charges = [
        charge
        for charge in successful
        if period_start_ts <= int(charge.get("created") or 0) < period_end_ts
    ]
    currency_totals: dict[str, float] = defaultdict(float)
    lifetime_currency_totals: dict[str, float] = defaultdict(float)
    for charge in successful:
        currency = (charge.get("currency") or "usd").lower()
        amount = float((charge.get("amount_captured") or charge.get("amount") or 0) - (charge.get("amount_refunded") or 0))
        lifetime_currency_totals[currency] += amount
        if period_start_ts <= int(charge.get("created") or 0) < period_end_ts:
            currency_totals[currency] += amount

    primary_currency = max(lifetime_currency_totals or {"usd": 0}, key=(lifetime_currency_totals or {"usd": 0}).get)
    recent_gross = currency_totals.get(primary_currency, 0)
    lifetime_gross = lifetime_currency_totals.get(primary_currency, 0)

    recent_balance = [
        txn
        for txn in balance_transactions
        if txn.get("reporting_category") == "charge"
        and (txn.get("currency") or "usd").lower() == primary_currency
        and period_start_ts <= int(txn.get("created") or 0) < period_end_ts
    ]
    recent_net = sum(float(txn.get("net") or 0) for txn in recent_balance)
    recent_fees = sum(float(txn.get("fee") or 0) for txn in recent_balance)

    return {
        "key": "veracityapi",
        "name": "VeracityAPI",
        "domain": "veracityapi.com",
        "color": "#336699",
        "source": "Stripe",
        "currency": primary_currency,
        "grossCentsPeriod": round(recent_gross, 2),
        "netCentsPeriod": round(recent_net, 2),
        "feesCentsPeriod": round(recent_fees, 2),
        "lifetimeGrossCents": round(lifetime_gross, 2),
        "successfulPaymentsPeriod": len(period_charges),
        "successfulPaymentsLifetime": len(successful),
        "updatedIso": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def revenue_cards(stripe_revenue: dict) -> dict:
    veracity = {
        "key": stripe_revenue["key"],
        "name": stripe_revenue["name"],
        "domain": stripe_revenue["domain"],
        "color": stripe_revenue.get("color", "#336699"),
        "total": money(stripe_revenue.get("grossCentsPeriod") or 0, stripe_revenue.get("currency") or "usd"),
        "label": f"{REVENUE_PERIOD_LABEL} gross collected",
        "source": "Stripe",
        "rows": [
            {"label": "Successful payments", "value": fmt(stripe_revenue.get("successfulPaymentsPeriod") or 0)},
            {"label": "Net after fees", "value": money(stripe_revenue.get("netCentsPeriod") or 0, stripe_revenue.get("currency") or "usd")},
            {"label": "Lifetime gross", "value": money(stripe_revenue.get("lifetimeGrossCents") or 0, stripe_revenue.get("currency") or "usd")},
        ],
    }
    return {
        "updatedIso": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "cards": [MANUAL_REVENUE_CARDS[0], MANUAL_REVENUE_CARDS[2], veracity, MANUAL_REVENUE_CARDS[1]],
    }


def load_existing_revenue_snapshot() -> dict | None:
    if not METRICS_HTML.exists():
        return None
    chart_match = re.search(r'const chartData = (.*?);', METRICS_HTML.read_text(), re.S)
    if not chart_match:
        return None
    try:
        chart = json.loads(chart_match.group(1))
    except json.JSONDecodeError:
        return None
    snapshot = chart.get("revenueSnapshot")
    if isinstance(snapshot, dict) and snapshot.get("cards"):
        return snapshot
    return None


def replace_chart_data(script_text: str, key: str, value: object) -> str:
    marker = f'"{key}":'
    start = script_text.index(marker)
    i = start + len(marker)
    # Skip value JSON object/array/primitive until the comma before the next top-level key.
    depth = 0
    in_string = False
    escaped = False
    value_start = i
    for j, ch in enumerate(script_text[i:], i):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            return script_text[:value_start] + json.dumps(value, separators=(",", ":")) + script_text[j:]
    return script_text[:value_start] + json.dumps(value, separators=(",", ":"))



def render_property_cards(data: dict) -> str:
    cards: list[str] = []
    for prop in data["properties"]:
        sources = prop.get("sources", [])
        max_sessions = max((row["sessions"] for row in sources), default=0)
        if sources:
            rows = "\n".join(
                f'''                            <li class="channel-item">
                                <span>{esc(row['sourceMedium'])}</span>
                                <strong>{fmt(row['sessions'])}</strong>
                                <span class="channel-track"><span class="channel-fill" style="width:{(row['sessions'] / max_sessions * 100 if max_sessions else 0):.1f}%;background:{esc(prop['color'])}"></span></span>
                            </li>'''
                for row in sources
            )
        else:
            rows = '                            <li class="empty-channels">No source / medium data yet.</li>'

        cards.append(
            f'''                <article class="property-card">
                    <div class="property-card-header">
                        <div>
                            <h3>{esc(prop['name'])}</h3>
                            <span class="property-domain">{esc(prop['domain'])}</span>
                        </div>
                        <div class="property-total">
                            <strong>{fmt(prop['totals']['sessions'])}</strong>
                            <span>sessions</span>
                        </div>
                    </div>
                    <div class="property-mini-chart"><canvas id="{esc(prop['key'])}Ga4Chart"></canvas></div>
                    <div class="subsection-label">Top source / medium</div>
                    <ol class="channel-list">
{rows}
                    </ol>
                </article>'''
        )
    return "\n".join(cards)


def render_search_console_cards(data: dict) -> str:
    cards: list[str] = []
    for prop in data.get("searchConsoleProperties", []):
        pages = prop.get("topPages", [])
        max_impressions = max((row["impressions"] for row in pages), default=0)
        if pages:
            rows = "\n".join(
                f'''                            <li class="channel-item">
                                <span title="{esc(row['page'])}">{esc(row['page'])}</span>
                                <strong>{fmt(row['clicks'])} / {compact(row['impressions'])}</strong>
                                <span class="channel-track"><span class="channel-fill" style="width:{(row['impressions'] / max_impressions * 100 if max_impressions else 0):.1f}%;background:{esc(prop['color'])}"></span></span>
                            </li>'''
                for row in pages
            )
        else:
            rows = '                            <li class="empty-channels">No page data yet.</li>'

        cards.append(
            f'''                <article class="property-card search-console-card">
                    <div class="property-card-header">
                        <div>
                            <h3>{esc(prop['name'])}</h3>
                            <span class="property-domain">{esc(prop['domain'])}</span>
                        </div>
                        <div class="property-total">
                            <strong>{fmt(prop['totals']['clicks'])}</strong>
                            <span>clicks · {compact(prop['totals']['impressions'])} impr.</span>
                        </div>
                    </div>
                    <div class="property-mini-chart"><canvas id="{esc(prop['key'])}GscChart"></canvas></div>
                    <div class="subsection-label">Top pages <span class="muted-inline">clicks / impressions</span></div>
                    <ol class="channel-list">
{rows}
                    </ol>
                </article>'''
        )
    return "\n".join(cards)


def render_revenue_cards(data: dict) -> str:
    revenue = data.get("revenueSnapshot") or {}
    if not revenue.get("cards"):
        return ""
    cards: list[str] = []
    for card in revenue.get("cards", []):
        rows = "\n".join(
            f'''                        <li class="channel-item"><span>{esc(row.get('label') or '')}</span><strong>{esc(row.get('value') or '')}</strong></li>'''
            for row in card.get("rows", [])
        )
        if card.get("topPrices"):
            rows += "\n" + "\n".join(
                f'''                        <li class="channel-item"><span>{esc(row.get('name') or 'Recurring price')}</span><strong>{money(row.get('mrrCents') or 0, row.get('currency') or 'usd')} MRR · {fmt(row.get('subscriptions') or 0)} subs</strong></li>'''
                for row in card.get("topPrices", [])
            )
        if not rows:
            rows = '                        <li class="empty-channels">No revenue data yet.</li>'
        cards.append(f'''                <article class="property-card revenue-card" style="--card-accent:{esc(card.get('color') or '#1a1a1a')}">
                    <div class="property-card-header">
                        <div>
                            <h3>{esc(card.get('name') or '')}</h3>
                            <span class="property-domain">{esc(card.get('source') or '')} · {esc(card.get('domain') or '')}</span>
                        </div>
                        <div class="property-total">
                            <strong>{esc(card.get('total') or '$0')}</strong>
                            <span>{esc(card.get('label') or 'revenue')}</span>
                        </div>
                    </div>
                    <ol class="channel-list revenue-list">
{rows}
                    </ol>
                </article>''')
    return "\n".join(cards)


def render_youtube_social_card(youtube: dict) -> str:
    series = youtube.get("timeSeries", {})
    chart_note = f"{series.get('label', 'Views by publish date')} · {series.get('range', '')}".strip(" ·")
    return f'''                <article class="property-card social-card">
                    <div class="property-card-header">
                        <div>
                            <h3>YouTube Shorts</h3>
                            <span class="property-domain">{esc(youtube.get('handle') or '@tabijiai')}</span>
                        </div>
                        <div class="property-total">
                            <strong>{fmt(youtube['totalViews'])}</strong>
                            <span>channel views</span>
                        </div>
                    </div>
                    <div class="chart-kicker">{esc(chart_note)}</div>
                    <div class="property-mini-chart"><canvas id="youtubeSocialChart"></canvas></div>
                    <div class="subsection-label">Signals</div>
                    <ol class="channel-list">
                        <li class="channel-item"><span>Subscribers</span><strong>{fmt(youtube['subscribers'])}</strong></li>
                        <li class="channel-item"><span>Videos</span><strong>{fmt(youtube['videos'])}</strong></li>
                        <li class="channel-item"><span>Tracked views</span><strong>{compact(youtube.get('trackedViews', 0))}</strong></li>
                    </ol>
                </article>'''


def render_youtube_detail_section(youtube: dict) -> str:
    top_rows = top_items(
        [
            {
                "title": row["title"],
                "url": row["url"],
                "stats": f"<span>{fmt(row['views'])} views</span>",
            }
            for row in youtube.get("topShorts", [])
        ]
    )
    return f'''        <!-- YouTube -->
        <div class="metric-section">
            <h2><span class="icon">▶️</span> YouTube</h2>
            <p class="section-desc">@<a href="https://youtube.com/@tabijiai">tabijiai</a> — AI-generated travel shorts. Public channel snapshot from YouTube; historical daily analytics will unlock after OAuth is expanded.</p>

            <div class="metric-row">
                <span class="metric-label">Subscribers</span>
                <span class="metric-value">{fmt(youtube['subscribers'])}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Videos</span>
                <span class="metric-value">{fmt(youtube['videos'])}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Channel Views</span>
                <span class="metric-value">{fmt(youtube['totalViews'])}</span>
            </div>

            <hr class="section-divider">
            <div class="subsection-label">Top Shorts by Views</div>
            <ul class="top-list">
{top_rows}
            </ul>
        </div>

'''


def update_html(data: dict) -> None:
    text = METRICS_HTML.read_text()

    # Keep the public metrics page limited to the portfolio-level cards. Legacy
    # Tabiji channel/detail sections are stripped here so nightly refreshes do
    # not accidentally republish private growth metrics.
    text = re.sub(r'<div class="updated-badge">Updated [^<]+</div>', f'<div class="updated-badge">Updated {esc(data["updatedLabel"])}</div>', text, count=1)

    # Remove the retired Aquarium section if it exists. The metrics page now
    # starts with the GA4 portfolio cards, and nightly refreshes should not
    # reinsert the aquarium.
    text = re.sub(
        r'        <!-- Portfolio Aquarium -->.*?(?=        <!-- Portfolio GA4 Snapshot -->|        <!-- Portfolio Search Console Snapshot -->|\n    </div>\n    </main>)',
        '',
        text,
        flags=re.S,
    )

    portfolio = f'''        <!-- Portfolio GA4 Snapshot -->
        <section class="portfolio-section" aria-labelledby="portfolio-ga4-heading">
            <h2 id="portfolio-ga4-heading"><span class="icon">📊</span> GA4 Portfolio Snapshot</h2>
            <p class="section-desc">Sessions over the last 90 days plus top source / medium rows for active properties. Ordered by total sessions.</p>
            <div class="property-grid">
{render_property_cards(data)}
            </div>
        </section>

'''
    # Each regex below looks ahead for ALL other section markers so the order
    # of sections in the rendered HTML doesn't change which content gets
    # captured. Revenue currently sits ABOVE GA4 in the rendered HTML; keep
    # both lookaheads defensive so a future reorder doesn't silently swallow
    # an adjacent section.
    text = re.sub(
        r'        <!-- Portfolio GA4 Snapshot -->.*?(?=        <!-- Revenue Snapshot -->|        <!-- Portfolio Search Console Snapshot -->|        <!-- Tabiji Social Snapshot -->|\n    </div>\n    </main>)',
        portfolio,
        text,
        flags=re.S,
    )

    revenue_cards = render_revenue_cards(data)
    if revenue_cards:
        revenue = f'''        <!-- Revenue Snapshot -->
        <section class="portfolio-section revenue-section" aria-labelledby="revenue-heading">
            <h2 id="revenue-heading"><span class="icon">💸</span> May 2026 Revenue Snapshot</h2>
            <p class="section-desc">Revenue snapshot for active projects. VeracityAPI usage revenue is pulled from Stripe read-only successful charges for May 2026.</p>
            <div class="property-grid revenue-grid">
{revenue_cards}
            </div>
        </section>

'''
        if '<!-- Revenue Snapshot -->' in text:
            text = re.sub(
                r'        <!-- Revenue Snapshot -->.*?(?=        <!-- Portfolio GA4 Snapshot -->|        <!-- Portfolio Search Console Snapshot -->|        <!-- Tabiji Social Snapshot -->|\n    </div>\n    </main>)',
                revenue,
                text,
                flags=re.S,
            )
        else:
            # Fallback: Revenue Snapshot now sits ABOVE the GA4 Snapshot. If
            # the marker is missing (first refresh after this code lands), seed
            # Revenue immediately before GA4 instead of before Search Console.
            text = text.replace('        <!-- Portfolio GA4 Snapshot -->', revenue + '        <!-- Portfolio GA4 Snapshot -->', 1)

    search_console = f'''        <!-- Portfolio Search Console Snapshot -->
        <section class="portfolio-section search-console-section" aria-labelledby="portfolio-gsc-heading">
            <h2 id="portfolio-gsc-heading"><span class="icon">🔎</span> Search Console Snapshot</h2>
            <p class="section-desc">Google Search Console clicks and impressions over the last 90 days for active properties. Ordered by total clicks.</p>
            <div class="property-grid">
{render_search_console_cards(data)}
            </div>
        </section>

'''
    if '<!-- Portfolio Search Console Snapshot -->' in text:
        text = re.sub(
            r'        <!-- Portfolio Search Console Snapshot -->.*?(?=\n    </div>\n    </main>|        <!-- Tabiji Social Snapshot -->|        <!-- Tabiji Metrics -->)',
            search_console,
            text,
            flags=re.S,
        )
    else:
        text = text.replace('\n    </div>\n    </main>', search_console + '    </div>\n    </main>', 1)

    # Remove any old detailed Tabiji sections if they are still present in a
    # checked-out copy. Keep the portfolio-level Tabiji Social Snapshot cards.
    legacy_start = text.find('        <!-- Tabiji Metrics -->')
    if legacy_start != -1:
        legacy_end = text.find('\n    </div>\n    </main>', legacy_start)
        if legacy_end == -1:
            raise RuntimeError('Could not find end of legacy Tabiji metrics block')
        text = text[:legacy_start] + text[legacy_end:]

    chart_match = re.search(r'const chartData = (.*?);', text, re.S)
    if not chart_match:
        raise RuntimeError("Could not find chartData")
    existing_chart = json.loads(chart_match.group(1))
    chart = {
        "portfolioGa4": {"labels": data["labels"], "properties": data["properties"]},
        "portfolioGsc": {"labels": data.get("gscLabels", data["labels"]), "properties": data.get("searchConsoleProperties", [])},
    }
    if data.get("revenueSnapshot"):
        chart["revenueSnapshot"] = data["revenueSnapshot"]
    if existing_chart.get("socialSnapshot"):
        chart["socialSnapshot"] = existing_chart["socialSnapshot"]
    text = text[: chart_match.start(1)] + json.dumps(chart, separators=(",", ":")) + text[chart_match.end(1) :]

    METRICS_HTML.write_text(text)

def current_head() -> str:
    return run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()


def deploy_status(head: str) -> str:
    gh = shutil.which("gh", path=PATH)
    if not gh:
        return "deploy status unknown: gh not found"
    deadline = time.time() + 300
    last = "deploy status unknown"
    while time.time() < deadline:
        proc = run(
            [
                gh,
                "run",
                "list",
                "--limit",
                "5",
                "--json",
                "headSha,status,conclusion,workflowName,url",
            ],
            check=False,
        )
        if proc.returncode == 0:
            try:
                runs = json.loads(proc.stdout)
                match = next((r for r in runs if r.get("headSha", "").startswith(head)), None)
                if match:
                    status = match.get("status")
                    conclusion = match.get("conclusion")
                    if status == "completed":
                        return f"deploy {conclusion or 'completed'}"
                    last = f"deploy {status}"
            except Exception as exc:
                last = f"deploy status parse failed: {exc}"
        time.sleep(10)
    return last


def load_previous_state() -> dict | None:
    if not STATE_PATH.exists():
        return None
    return json.loads(STATE_PATH.read_text())


def save_state(data: dict, head: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "updatedIso": data["updatedIso"],
        "commit": head,
        "totalSessions": sum(prop["totals"]["sessions"] for prop in data["properties"]),
        "properties": {prop["key"]: {"name": prop["name"], "sessions": prop["totals"]["sessions"]} for prop in data["properties"]},
    }
    STATE_PATH.write_text(json.dumps(state, indent=2))


def movement_lines(previous: dict | None, data: dict) -> list[str]:
    if not previous:
        return ["No previous nightly baseline yet; saved tonight as the baseline."]

    lines: list[str] = []
    current_total = sum(prop["totals"]["sessions"] for prop in data["properties"])
    previous_total = previous.get("totalSessions", 0)
    if previous_total:
        delta = (current_total - previous_total) / previous_total
        if abs(delta) >= THRESHOLD:
            direction = "up" if delta > 0 else "down"
            lines.append(f"⚠️ Total portfolio traffic {direction} {delta:+.1%}: {fmt(previous_total)} → {fmt(current_total)} sessions")

    previous_props = previous.get("properties", {})
    for prop in data["properties"]:
        old = previous_props.get(prop["key"], {}).get("sessions")
        new = prop["totals"]["sessions"]
        if old is None:
            continue
        if old == 0 and new > 0:
            lines.append(f"⚠️ {prop['name']} traffic started from zero: 0 → {fmt(new)} sessions")
        elif old:
            delta = (new - old) / old
            if abs(delta) >= THRESHOLD:
                direction = "up" if delta > 0 else "down"
                lines.append(f"⚠️ {prop['name']} traffic {direction} {delta:+.1%}: {fmt(old)} → {fmt(new)} sessions")
    return lines or ["No ±25% total-traffic movements vs previous nightly baseline."]


def post_slack(message: str, dry_run: bool = False) -> None:
    if dry_run:
        print("DRY RUN Slack message:\n" + message)
        return
    openclaw = shutil.which("openclaw", path=PATH) or "/opt/homebrew/bin/openclaw"
    run([openclaw, "message", "send", "--channel", "slack", "--target", CHANNEL, "--message", message], check=False, capture=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-post", action="store_true", help="Do everything except posting to Slack")
    parser.add_argument("--no-push", action="store_true", help="Update files but do not commit/push")
    parser.add_argument("--skip-revenue", action="store_true", help="Keep the existing revenue snapshot unchanged")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)

    if not args.no_push:
        ensure_git_push_auth()
    run(["git", "pull", "--rebase", "--autostash", "origin", "main"], capture=True)
    fetch = run(["node", str(FETCHER)], capture=True)
    data = json.loads(fetch.stdout)
    warnings: list[str] = []
    if args.skip_revenue:
        fallback_revenue = load_existing_revenue_snapshot()
        if not fallback_revenue:
            raise RuntimeError("Cannot skip revenue refresh because no existing revenue snapshot was found")
        data["revenueSnapshot"] = fallback_revenue
    else:
        try:
            data["revenueSnapshot"] = revenue_cards(fetch_stripe_usage_revenue())
        except Exception as exc:
            fallback_revenue = load_existing_revenue_snapshot()
            if not fallback_revenue:
                raise
            data["revenueSnapshot"] = fallback_revenue
            warning = f"⚠️ VeracityAPI revenue unchanged: {exc}"
            warnings.append(warning)
            print(warning, file=sys.stderr)

    previous = load_previous_state()
    update_html(data)

    status = run(["git", "status", "--short"], capture=True).stdout.strip()
    changed = bool(status)
    head = current_head()
    deploy = "no deploy needed"

    if changed and not args.no_push:
        run(["git", "add", "metrics/index.html", "scripts/fetch-ga4-portfolio.js", "scripts/update-metrics-cron.py"], capture=True)
        run(["git", "commit", "-m", "Refresh metrics page data"], capture=True)
        run_with_retry(["git", "push", "origin", "main"], attempts=2, delay=10, capture=True)
        head = current_head()
        deploy = deploy_status(head)
    elif args.no_push:
        deploy = "not pushed (--no-push)"

    save_state(data, head)

    totals = {prop["name"]: prop["totals"]["sessions"] for prop in data["properties"]}
    movements = movement_lines(previous, data)
    message = "\n".join(
        [
            f"✅ Updated zonted.com/metrics/ ({data['rangeLabel']})",
            f"Commit: `{head}` · {deploy}",
            "Sessions: " + ", ".join(f"{name} {fmt(value)}" for name, value in totals.items()),
            *warnings,
            *movements,
        ]
    )
    post_slack(message, dry_run=args.no_post)
    print(message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        error_msg = f"❌ Failed to update zonted.com/metrics/: {exc}"
        print(error_msg, file=sys.stderr)
        if "--no-post" not in sys.argv:
            try:
                post_slack(error_msg)
            except Exception:
                pass
        raise
