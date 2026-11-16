#!/usr/bin/env python3
"""
Build script for zonted.com
Scans article files, generates homepage index, hub pages, sitemap, RSS feed,
and injects next/prev + share links into articles.

Usage: python3 scripts/build.py
Run from the repo root.
"""

import os
import re
import html
import json
import subprocess
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://zonted.com"

FALLBACK_DATES = {
    "posts/what-is-ai-self-healing": "2026-03-29",
    "posts/veo3-vs-hailuo-minimax": "2026-03-11",
    "posts/nano-banana-vs-grok": "2026-03-14",
    "posts/best-short-form-video-services": "2026-03-01",
    "posts/ai-resilience-planning": "2026-03-27",
    "posts/ai-music-generation-comparison": "2026-03-11",
    "posts/ai-image-generation-comparison": "2026-03-11",
}

# og:image URLs that 404 on R2. Treat as no-image; the row will skip the
# thumb column entirely. Move to a working URL or re-upload the asset to
# img.zonted.com to bring the thumbnail back.
BROKEN_IMAGES = {
    "https://img.zonted.com/og/ai-reels-what-actually-works.jpg",
    "https://img.zonted.com/og/makeugc-review.jpg",
    "https://img.zonted.com/og/wavespeed-review.jpg",
    # Returns 200 but the asset is a 117-byte stub, not the actual hero image
    "https://img.zonted.com/resources/what-is-ai-self-healing/hero-bg.jpg",
}

# Per-slug thumbnail override. Wins over og:image filtering — useful when
# og:image is the generic owl logo or a broken/stub asset, but the article
# body has a real hero image we can point at instead.
SLUG_THUMB_OVERRIDES = {
    "posts/ai-desk-figr-earnings": "/posts/ai-desk-figr-earnings/figure-metrics-dashboard.png",
    "posts/stakes-priming": "/posts/stakes-priming/img/tabiji-verdict.png",
    "posts/stakes-priming-surface-area": "https://img.zonted.com/resources/stakes-priming-surface-area/twelve-deliverables.png",
    "posts/ai-psychosis": "/posts/ai-psychosis/img/cyberpsychosis.avif",
    "posts/openclaw-claude-ban-ai-model-replacement": "https://img.zonted.com/resources/cleanshot-claude-ban.png",
    "posts/rise-of-the-ai-influencer": "/posts/rise-of-the-ai-influencer/img/yangmunus-instagram-profile.png",
    "posts/slop-iterate-curate-ai-content": "https://img.zonted.com/resources/slop-iterate-curate/killed-natural-attractions.png",
    "posts/true-cost-of-ai-content-production": "https://img.zonted.com/resources/true-cost-of-ai-content-production/google-cloud-billing-march-2026.png",
    "posts/veo3-vs-hailuo-minimax": "https://img.zonted.com/resources/video-generation-comparison/capybara-source.jpg",
    "posts/makeugc": "https://img.zonted.com/resources/makeugc-review/content-library.jpg",
    "posts/wavespeed": "https://img.zonted.com/resources/wavespeed-review/ws-dashboard.png",
}

# ---------------------------------------------------------------------------
# Category assignment
# ---------------------------------------------------------------------------

def get_category(slug, title):
    title_lower = title.lower()
    slug_lower = slug.lower()
    if 'review' in slug_lower or 'review:' in title_lower:
        return 'Reviews'
    if any(w in title_lower for w in ['vs', 'comparison', 'compared', 'showdown', 'best ai']):
        return 'Comparisons'
    if any(w in slug_lower for w in ['postmortem', 'retiring-', 'retrospective']) or any(w in title_lower for w in ['post-mortem', 'postmortem', 'shut down']):
        return 'Post-Mortems'
    if any(w in slug_lower for w in [
        'trading', 'trade-log', 'nothing-looked-wrong', 'token-launch',
        'qqq-spy', 'figr-earnings', 'mdb-option', 'google-trends-stock',
        '13f-congress', 'paper-fund', 'sol-fund', 'back-to-the-tables',
        'contamination',
    ]):
        return 'Autonomous Trading & Markets'
    if any(w in slug_lower for w in ['aeo-', 'ctr-gap', 'google-zero', 'training-data-is-the-moat', 'agentic-data-enrichment']):
        return 'AEO & Search'
    if any(w in title_lower for w in ['what is', 'how to', 'guide', 'planning', "do's & don'ts", 'playbook']):
        return 'Guides'
    if any(w in title_lower for w in ['reels', 'instagram', 'youtube', 'tiktok', 'short-form', 'video services', 'viral video', '18m views', 'true cost of ai', 'pixel sprites', 'ai slop is necessary']):
        return 'Production'
    return 'AI Agents & Systems'


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(filepath, slug):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    head_match = re.search(r'<head[^>]*>(.*?)</head>', content, re.DOTALL | re.IGNORECASE)
    head = head_match.group(1) if head_match else content

    # Title
    title_match = re.search(r'<title>(.*?)</title>', head, re.DOTALL | re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else slug
    # Strip suffixes
    for suffix in [' — zonted.com', ' — Zonted', ' &mdash; zonted.com', ' &mdash; Zonted']:
        if title.endswith(suffix):
            title = title[:-len(suffix)]
    # Also handle HTML entity dash
    title = re.sub(r'\s*(?:—|&mdash;)\s*(?:zonted\.com|Zonted)\s*$', '', title)

    # Description — backreference the opening quote so apostrophes inside
    # the content don't truncate (e.g. "tabiji.ai's production HTML…").
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=(["\'])(.*?)\1', head, re.IGNORECASE)
    description = html.unescape(desc_match.group(2)) if desc_match else ''

    # Date from article:published_time
    date_match = re.search(r'<meta\s+property=["\']article:published_time["\']\s+content=["\'](\d{4}-\d{2}-\d{2})', head, re.IGNORECASE)
    date_str = None
    if date_match:
        date_str = date_match.group(1)
    elif slug in FALLBACK_DATES:
        date_str = FALLBACK_DATES[slug]

    # Modified date from article:modified_time or JSON-LD dateModified
    mod_match = re.search(r'<meta\s+property=["\']article:modified_time["\']\s+content=["\'](\d{4}-\d{2}-\d{2})', head, re.IGNORECASE)
    if not mod_match:
        mod_match = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"', head)
    modified_date = mod_match.group(1) if mod_match else date_str

    # On-page H1
    h1_match = re.search(r'<h1\b[^>]*>(.*?)</h1>', content, re.DOTALL | re.IGNORECASE)
    h1_text = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', h1_match.group(1)))).strip() if h1_match else html.unescape(title)

    # Reading time
    rt_match = re.search(r'(\d+)\s*min\s*read', content, re.IGNORECASE)
    reading_time = int(rt_match.group(1)) if rt_match else None

    # og:image — backreferenced quote (same fix as description). Filter out
    # the generic tabiji-owl-logo default + URLs we've confirmed 404 so the
    # row simply omits the thumb column. operator-notes.png is the site-wide
    # OG fallback for posts without a real hero — also treat as "no image"
    # so the post index doesn't show 25+ identical thumbnails.
    img_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=(["\'])(.*?)\1', head, re.IGNORECASE)
    image = img_match.group(2) if img_match else ''
    if ('tabiji-owl-logo' in image or 'zonted-og.png' in image
            or 'bernard-huang-headshot' in image or 'operator-notes' in image
            or image in BROKEN_IMAGES):
        image = ''
    # Slug override wins (e.g. og:image was the owl, but the body has a hero)
    if slug in SLUG_THUMB_OVERRIDES:
        image = SLUG_THUMB_OVERRIDES[slug]

    category = get_category(slug, title)

    return {
        'title': html.unescape(title),
        'h1': h1_text,
        'description': description,
        'date': date_str,
        'modified_date': modified_date,
        'reading_time': reading_time,
        'slug': slug,
        'category': category,
        'image': image,
        'filepath': filepath,
    }


def scan_articles():
    articles = []
    section_dir = os.path.join(ROOT, 'posts')
    if os.path.isdir(section_dir):
        for name in os.listdir(section_dir):
            article_dir = os.path.join(section_dir, name)
            index_file = os.path.join(article_dir, 'index.html')
            if os.path.isdir(article_dir) and os.path.isfile(index_file):
                slug = f"posts/{name}"
                meta = extract_metadata(index_file, slug)
                articles.append(meta)

    # Sort by date (newest first), tie-break by slug. File mtime cannot be a
    # stable tie-breaker because this build rewrites article files when it
    # refreshes generated blocks, which made same-day posts swap order on
    # every run.
    articles.sort(key=lambda a: (a['date'] or '0000-00-00', a['slug']), reverse=True)
    return articles


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

def format_date_short(date_str):
    """Format YYYY-MM-DD to 'Apr 9, 2026'."""
    if not date_str:
        return ''
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.strftime('%b %-d, %Y')


def format_date_rfc822(date_str):
    """Format YYYY-MM-DD to RFC 822 for RSS."""
    if not date_str:
        return ''
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # RFC 822: e.g. Wed, 09 Apr 2026 00:00:00 +0000
    return dt.strftime('%a, %d %b %Y 00:00:00 +0000')


# ---------------------------------------------------------------------------
# Entry list HTML generation
# ---------------------------------------------------------------------------

SHIPPED_FRESH_DAYS = 7
"""Freshness window for the JUST PUBLISHED stamp on /posts/. The newest post
gets stamped only if its date is within this many days of the build run.
After that, the stamp disappears until a new post ships."""


def is_shipped(article):
    """True if this article should get the JUST PUBLISHED stamp on /posts/."""
    if not article.get('date'):
        return False
    try:
        dt = datetime.strptime(article['date'], '%Y-%m-%d')
    except (ValueError, TypeError):
        return False
    age_days = (datetime.now() - dt).days
    return 0 <= age_days < SHIPPED_FRESH_DAYS


def make_entry_row(article, mark_shipped=False):
    date_display = format_date_short(article['date']) if article['date'] else ''
    title = html.escape(article['title'])
    dek = html.escape(article.get('description', '') or '')
    image = article.get('image', '')
    thumb = ''
    if image:
        thumb = (
            f'                        <a href="/{article["slug"]}/" class="zn-row-thumb" tabindex="-1">'
            f'<img src="{html.escape(image)}" alt="" loading="lazy"></a>\n'
        )
    left_html = (
        f'                    <div class="zn-row-left">\n'
        f'                        <span class="zn-row-date">{date_display}</span>\n'
        f'{thumb}'
        f'                    </div>'
    )

    row_classes = 'zn-row'
    stamp_html = ''
    if mark_shipped:
        row_classes += ' zn-row-shipped'
        stamp_html = (
            '\n                    <div class="zn-shipped-stamp" aria-hidden="true">'
            '★ JUST PUBLISHED</div>'
        )

    return (
        f'                <li class="{row_classes}">\n'
        f'{left_html}\n'
        f'                    <div class="zn-row-content">\n'
        f'                        <a href="/{article["slug"]}/" class="zn-row-title">{title}</a>\n'
        f'                        <p class="zn-row-dek">{dek}</p>\n'
        f'                    </div>{stamp_html}\n'
        f'                </li>'
    )


# ---------------------------------------------------------------------------
# Homepage generation
# ---------------------------------------------------------------------------

FILTER_BAR_HTML = '''            <div class="filter-bar" style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
                <button class="filter-btn active" data-filter="all" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--text);color:var(--bg);cursor:pointer;">All</button>
                <button class="filter-btn" data-filter="reviews" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-muted);cursor:pointer;">Reviews</button>
                <button class="filter-btn" data-filter="comparisons" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-muted);cursor:pointer;">Comparisons</button>
                <button class="filter-btn" data-filter="guides" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-muted);cursor:pointer;">Guides</button>
                <button class="filter-btn" data-filter="production" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-muted);cursor:pointer;">Production</button>
                <button class="filter-btn" data-filter="opinion" style="font-family:'Inter',system-ui,sans-serif;font-size:0.8rem;font-weight:500;padding:4px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-muted);cursor:pointer;">Opinion</button>
            </div>'''

FILTER_JS = '''<!-- FILTER_JS_START -->
<script>
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;
        document.querySelectorAll('.filter-btn').forEach(b => {
            b.style.background = 'var(--bg)';
            b.style.color = 'var(--text-muted)';
            b.classList.remove('active');
        });
        btn.style.background = 'var(--text)';
        btn.style.color = 'var(--bg)';
        btn.classList.add('active');
        document.querySelectorAll('.entry-row').forEach(row => {
            if (filter === 'all' || row.dataset.category === filter) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
});
</script>
<!-- FILTER_JS_END -->'''


def generate_homepage(articles):
    filepath = os.path.join(ROOT, 'index.html')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Homepage shows only the 5 most recent posts; "Read all →" link in
    # the section header points to /posts/ for the full hub.
    homepage_articles = articles[:5]
    rows = [make_entry_row(a) for a in homepage_articles]
    entry_html = '\n'.join(rows)

    new_block = (
        f'<!-- ENTRY_LIST_START -->\n'
        f'                <ul class="zn-rows">\n'
        f'{entry_html}\n'
        f'                </ul>\n'
        f'                <!-- ENTRY_LIST_END -->'
    )

    # Replace between markers
    content = re.sub(
        r'<!-- ENTRY_LIST_START -->.*?<!-- ENTRY_LIST_END -->',
        new_block,
        content,
        flags=re.DOTALL
    )

    # Update article count
    count = len(articles)
    content = re.sub(
        r'\d+ articles,',
        f'{count} articles,',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return count


# ---------------------------------------------------------------------------
# Posts hub generation
# ---------------------------------------------------------------------------

def generate_posts_hub(articles):
    filepath = os.path.join(ROOT, 'posts', 'index.html')
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Mark the newest post as "shipped" if it's within the freshness window.
    # Stamps disappear once the post ages past SHIPPED_FRESH_DAYS.
    rows = [
        make_entry_row(a, mark_shipped=(i == 0 and is_shipped(a)))
        for i, a in enumerate(articles)
    ]
    entry_html = '\n'.join(rows)

    new_block = (
        f'<!-- ENTRY_LIST_START -->\n'
        f'                <ul class="zn-rows">\n'
        f'{entry_html}\n'
        f'                </ul>\n'
        f'                <!-- ENTRY_LIST_END -->'
    )

    content = re.sub(
        r'<!-- ENTRY_LIST_START -->.*?<!-- ENTRY_LIST_END -->',
        new_block,
        content,
        flags=re.DOTALL
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return len(articles)


# ---------------------------------------------------------------------------
# Sitemap generation
# ---------------------------------------------------------------------------

def git_lastmod(rel_path, fallback):
    """Return last-modified YYYY-MM-DD for a static file via git, falling back cleanly."""
    try:
        res = subprocess.run(
            ['git', 'log', '-1', '--format=%cs', '--', rel_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = res.stdout.strip()
        if res.returncode == 0 and re.match(r'^\d{4}-\d{2}-\d{2}$', out):
            return out
    except Exception:
        pass
    return fallback


def generate_sitemap(articles):
    today = datetime.now().strftime('%Y-%m-%d')
    post_dates = [a.get('modified_date') or a.get('date') for a in articles if a.get('modified_date') or a.get('date')]
    max_post_date = max(post_dates) if post_dates else today
    urls = []

    # Homepage & Posts hub reflect newest published/modified post
    urls.append(('/', '1.0', max_post_date))
    urls.append(('/posts/', '0.8', max_post_date))
    # Hubs & Games use per-file git commit date (fallback to max_post_date)
    urls.append(('/portfolio/', '0.8', git_lastmod('portfolio/index.html', max_post_date)))
    urls.append(('/ai-stack/', '0.8', git_lastmod('ai-stack/index.html', max_post_date)))
    urls.append(('/about/', '0.7', git_lastmod('about/index.html', max_post_date)))
    urls.append(('/games/', '0.7', git_lastmod('games/index.html', max_post_date)))
    urls.append(('/games/graveyard/', '0.6', git_lastmod('games/graveyard/index.html', max_post_date)))
    urls.append(('/games/life-of-fry/', '0.6', git_lastmod('games/life-of-fry/index.html', max_post_date)))
    urls.append(('/games/run-to-rebecca/', '0.6', git_lastmod('games/run-to-rebecca/index.html', max_post_date)))

    # Articles
    for a in articles:
        lastmod = a.get('modified_date') or a['date'] or today
        urls.append((f'/{a["slug"]}/', '0.7', lastmod))

    xml_entries = []
    for loc, priority, lastmod in urls:
        xml_entries.append(
            f'  <url>\n'
            f'    <loc>{SITE_URL}{loc}</loc>\n'
            f'    <lastmod>{lastmod}</lastmod>\n'
            f'    <priority>{priority}</priority>\n'
            f'  </url>'
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(xml_entries) + '\n'
        '</urlset>\n'
    )

    filepath = os.path.join(ROOT, 'sitemap.xml')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(sitemap)

    return len(urls)


# ---------------------------------------------------------------------------
# RSS feed generation
# ---------------------------------------------------------------------------

def _strip_tags_clean(s):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))).strip()


def extract_tldr(content):
    """Extract structured TL;DR {thesis, bullets, tail} using a <div>-depth counter.

    Matches <div class="tldr"> as well as variants carrying an id attribute such as
    <div class="tldr" id="key-takeaways"> or <div class="tldr" id="tldr">.
    """
    m = re.search(r'<div\b[^>]*\bclass=["\'][^"\']*\btldr\b[^"\']*["\'][^>]*>', content, re.IGNORECASE)
    if not m:
        return None
    pos = m.end()
    depth = 1
    token_re = re.compile(r'<div(?:\s[^>]*|)>|</div>', re.IGNORECASE)
    end_idx = None
    for tok_m in token_re.finditer(content, pos):
        if tok_m.group(0).lower().startswith('<div'):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                end_idx = tok_m.start()
                break
    tldr_html = content[m.end():end_idx] if end_idx is not None else content[m.end():m.end() + 8000]
    thesis_m = re.search(r'<p\b[^>]*\bclass=["\'][^"\']*\btldr-thesis\b[^"\']*["\'][^>]*>(.*?)</p>', tldr_html, re.DOTALL | re.IGNORECASE)
    thesis = _strip_tags_clean(thesis_m.group(1)) if thesis_m else ''
    bullets = [_strip_tags_clean(b) for b in re.findall(r'<li\b[^>]*>(.*?)</li>', tldr_html, re.DOTALL | re.IGNORECASE)]
    bullets = [b for b in bullets if b]
    tail_m = re.search(r'<p\b[^>]*\bclass=["\'][^"\']*\btldr-tail\b[^"\']*["\'][^>]*>(.*?)</p>', tldr_html, re.DOTALL | re.IGNORECASE)
    tail = _strip_tags_clean(tail_m.group(1)) if tail_m else ''
    return {'thesis': thesis, 'bullets': bullets, 'tail': tail}


def extract_excerpt(filepath):
    """Plain-text excerpt for content:encoded — dropcap lead + TL;DR thesis and
    bullets when present, else the first couple of substantial paragraphs.
    Gives AI/RSS readers real content without shipping the full article HTML."""
    try:
        content = open(filepath, encoding='utf-8').read()
    except OSError:
        return ''
    parts = []
    m = re.search(r'<p class="dropcap">(.*?)</p>', content, re.DOTALL)
    if m:
        parts.append(_strip_tags_clean(m.group(1)))
    tldr = extract_tldr(content)
    if tldr:
        if tldr['thesis']:
            parts.append(tldr['thesis'])
        if tldr['bullets']:
            parts.append(' • '.join(tldr['bullets']))
    if not parts:
        body = re.search(r'<div class="article-body">(.*?)$', content, re.DOTALL)
        scope = body.group(1) if body else content
        for para in re.findall(r'<p[^>]*>(.*?)</p>', scope, re.DOTALL):
            txt = _strip_tags_clean(para)
            if len(txt) > 80:
                parts.append(txt)
            if len(parts) >= 2:
                break
    out = ' '.join(parts)
    return out[:1800].rsplit(' ', 1)[0] + '…' if len(out) > 1800 else out


def generate_feed(articles):
    items = []
    for a in articles:
        pub_date = format_date_rfc822(a['date']) if a['date'] else ''
        desc_escaped = html.escape(a['description'])
        link = f'{SITE_URL}/{a["slug"]}/'
        excerpt = extract_excerpt(a['filepath'])
        content_block = (
            f'      <content:encoded><![CDATA[{excerpt}]]></content:encoded>\n'
            if excerpt else ''
        )
        items.append(
            f'    <item>\n'
            f'      <title>{html.escape(a["title"])}</title>\n'
            f'      <link>{link}</link>\n'
            f'      <description>{desc_escaped}</description>\n'
            + content_block +
            f'      <pubDate>{pub_date}</pubDate>\n'
            f'      <author>bernard@zonted.com (Bernard Huang)</author>\n'
            f'      <guid isPermaLink="true">{link}</guid>\n'
            f'    </item>'
        )

    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">\n'
        '  <channel>\n'
        '    <title>Zonted</title>\n'
        f'    <link>{SITE_URL}/</link>\n'
        '    <description>Operator notes on AI in production by Bernard Huang — autonomous agent systems, multi-venue AI trading (Rig++), model benchmarks, and cost economics. Receipts included.</description>\n'
        '    <language>en-us</language>\n'
        f'    <lastBuildDate>{format_date_rfc822(datetime.now().strftime("%Y-%m-%d"))}</lastBuildDate>\n'
        f'    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml" />\n'
        + '\n'.join(items) + '\n'
        '  </channel>\n'
        '</rss>\n'
    )

    filepath = os.path.join(ROOT, 'feed.xml')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(feed)

    return len(items)


# ---------------------------------------------------------------------------
# llms.txt / llms-full.txt generation
# ---------------------------------------------------------------------------
# Hand-written intro preserved verbatim; the post list regenerates on every
# build so AI crawlers always see the complete, current archive.

LLMS_INTRO = """# Zonted

> Honest writing on AI in production by Bernard Huang. Operator notes from someone building fully autonomous AI businesses — agent workflows, model selection, cost economics, and what actually breaks. Receipts included.

Zonted is Bernard Huang's personal site. The angle is non-commodity: specific systems, real numbers from production, counterintuitive takes earned from running AI pipelines daily. Bernard runs Tabiji (an AI-driven travel publisher), PixelForge, AgentTune, and other agentic businesses, and writes about the systems behind them — token herding agent swarms, cron-shipped content pipelines, API economics, model benchmarks. He founded Clearscope (the bootstrapped SEO content optimization platform), ran it for a decade, and stepped away in mid-2026. His current deep-dive is autonomous markets: running **Rig++** (https://zonted.com/posts/ai-trading-rig/ · live P&L at https://psyduckler.com/pnl/), an agent-first multi-venue trading operation across Kalshi, Polymarket, Hyperliquid, and OpenSea powered by Claude Opus 5.5, tokay.io, Console MCP/Postgres, and Duet, alongside three open agent-friendly prediction-market data platforms (https://groundhog.markets, https://parrot.markets, and https://chameleons.markets). He treats AI the same way he treats search: empirical, measured, skeptical of received wisdom.

> **For AI agents:** Every article also has a clean, zero-boilerplate Markdown mirror at `https://zonted.com/posts/<slug>/index.md` (linked below and advertised via `<link rel="alternate" type="text/markdown">`).

## What this site covers

- **Token herding** — orchestrating large numbers of AI calls across models, weighing cost vs. quality per task
- **AI video, image, and music generation** — first-hand benchmarks of every commercial model worth running
- **Content pipelines** — Reels, comics, articles, video produced end-to-end by agent swarms
- **Search and answer-engine optimization (AEO)** — what works for AI-driven search after Google Zero
- **API economics** — cost-per-call analysis, infrastructure tradeoffs, the dying scraping economy
- **Operator philosophy** — why "slop, iterate, curate" beats hand-crafting; why owning the stack matters
- **Autonomous & AI-assisted trading** — Rig++ multi-venue prediction-market trading (Kalshi, Polymarket, Hyperliquid, OpenSea), agent-first architecture, weather & mention market microstructure, and postmortems from retired autonomous paper funds
"""

LLMS_OUTRO = """## Sections

- [All posts](https://zonted.com/posts/): Complete archive — {count} essays, updated regularly
- [Projects](https://zonted.com/portfolio/): Every project shipped (Tabiji, Rig++, groundhog.markets, parrot.markets, chameleons.markets, PixelForge, AgentTune) and the postmortem graveyard
- [Metrics / Live P&L](https://psyduckler.com/pnl/): Live trading P&L and strategy metrics for Rig++
- [AI Stack](https://zonted.com/ai-stack/): The tools and models actually running in production right now
- [Games](https://zonted.com/games/): Browser games built in the lab, including playable project post-mortems
- [About](https://zonted.com/about/): Background, current focus, how to get in touch

## Companion prediction-market data platforms (for agents & humans)

- [groundhog.markets](https://groundhog.markets/): Open weather forecasts blended for Kalshi and Polymarket weather markets (highs, lows, rain across 77 cities) with agent API
- [parrot.markets](https://parrot.markets/): Open data for Kalshi and Polymarket earnings-call mention markets — transcripts, word history, calibrated probabilities, `llms.txt`, and HTTP MCP server (`https://parrot.markets/mcp`)
- [chameleons.markets](https://chameleons.markets/): Polymarket copy-trading ratings, bot detection, and 90-day modelled ROIC across categories

## Feeds

- [RSS](https://zonted.com/feed.xml) — full archive with content excerpts
- [Email newsletter](https://zonted.com/#subscribe) — one email when a new post ships, no drip sequences

## Author

Bernard Huang. Based in Austin, TX. Founder of [Clearscope](https://clearscope.io) — the bootstrapped SEO content optimization platform he ran for a decade before stepping away fully in 2026. Background in SEO/content/affiliate going back ~15 years, and in online poker before that. Currently building Tabiji, AgentTune, PixelForge, and other agentic businesses, and running Rig++ (autonomous multi-venue trading across Kalshi, Polymarket, Hyperliquid, and OpenSea with Claude Opus 5.5 and tokay.io) alongside open prediction-market data platforms (groundhog.markets, parrot.markets, chameleons.markets). Writes at zonted.com daily-ish.
"""

H2_NOISE = {'Get the next post by email.'}

def generate_llms(articles):
    n = len(articles)
    lines = [LLMS_INTRO]
    lines.append(f'## All posts ({n})\n')
    for a in articles:
        desc = (a.get('description') or '').strip()
        date = f" ({a['date']})" if a['date'] else ''
        md_url = f'{SITE_URL}/{a["slug"]}/index.md'
        lines.append(f'- [{a["title"]}]({SITE_URL}/{a["slug"]}/): {desc}{date} · [Markdown]({md_url})')
    lines.append('')
    lines.append(LLMS_OUTRO.format(count=n))
    with open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    full = [LLMS_INTRO, f'## All posts, with evidence digests & outlines ({n})\n']
    for a in articles:
        try:
            content = open(a['filepath'], encoding='utf-8').read()
        except OSError:
            content = ''
        tldr = extract_tldr(content)
        h2s = []
        for raw in re.findall(r'<h2[^>]*>(.*?)</h2>', content, re.DOTALL):
            txt = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', raw))).strip()
            if txt and txt not in H2_NOISE and len(txt) < 90:
                h2s.append(txt)
        meta_parts = [f'{SITE_URL}/{a["slug"]}/', f'Markdown: {SITE_URL}/{a["slug"]}/index.md']
        if a['date']:
            meta_parts.append(a['date'])
        if a.get('category'):
            meta_parts.append(a['category'])
        if a.get('reading_time'):
            meta_parts.append(f"{a['reading_time']} min read")
        full.append(f'### {a["title"]}')
        full.append(' · '.join(meta_parts))
        if a.get('description'):
            full.append(a['description'])
        if tldr:
            if tldr['thesis']:
                full.append(f"Thesis: {tldr['thesis']}")
            if tldr['bullets']:
                full.append('Key takeaways:')
                for b in tldr['bullets']:
                    full.append(f'- {b}')
        if h2s:
            full.append('Sections: ' + ' · '.join(h2s[:14]))
        full.append('')
    full.append(LLMS_OUTRO.format(count=n))
    with open(os.path.join(ROOT, 'llms-full.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(full))
    return n


# ---------------------------------------------------------------------------
# Cleanup: strip nav links and fix back link alignment
# ---------------------------------------------------------------------------

def strip_nav_links(articles):
    """Remove share-on-X + next/prev nav links from all articles."""
    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if '<!-- NAV_LINKS_START -->' in content and '<!-- NAV_LINKS_END -->' in content:
            content = re.sub(
                r'\n*<!-- NAV_LINKS_START -->.*?<!-- NAV_LINKS_END -->\n*',
                '\n',
                content,
                flags=re.DOTALL
            )
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1

    return count


def strip_share_and_related(articles):
    """Remove end-of-article share buttons + Keep Reading blocks site-wide.

    Two historical patterns exist:
      A) Older posts: <hr> + <div class="share-buttons"> + <div class="related-posts">
      B) Newer posts: a single <div> with a "Share on X →" link

    This pass strips both so they don't accrete again on subsequent builds.
    """
    # The related-posts <div> contains a nested <div class="related-label">,
    # so a non-greedy `.*?</div>` would close at the inner div's closer and
    # leave the <ul> + outer </div> behind. The sub-pattern below spans the
    # full block by anchoring on the inner <ul class="related-list">…</ul>
    # before allowing </div> to close.
    related_div = (
        r'<div class="related-posts">\s*'
        r'(?:<div class="related-label">[^<]*</div>\s*)?'
        r'<ul class="related-list">.*?</ul>\s*'
        r'</div>'
    )

    # Pattern A: hr + share-buttons + related-posts (related block optional).
    pat_share_buttons = re.compile(
        r'\n*\s*<hr[^>]*style="[^"]*margin:\s*3rem\s*0[^"]*"[^>]*>\s*'
        r'<div class="share-buttons">.*?</div>\s*'
        r'(?:' + related_div + r'\s*)?',
        re.DOTALL
    )
    # Variant where the hr is omitted but share-buttons + related are still present.
    pat_share_no_hr = re.compile(
        r'\n*\s*<div class="share-buttons">.*?</div>\s*'
        r'(?:' + related_div + r'\s*)?',
        re.DOTALL
    )
    # Pattern B: standalone "Share on X →" div (no LinkedIn / Copy Link).
    pat_share_on_x = re.compile(
        r'\n*<div style="max-width:660px;margin:2rem auto;padding:0 2rem;text-align:center;">\s*'
        r'<a href="https://x\.com/intent/tweet[^"]*"[^>]*>Share on X[^<]*</a>\s*'
        r'</div>\s*',
        re.DOTALL
    )
    # Pattern C: an h2 "Related reading"/"Related"/"Related Resources" heading
    # immediately followed by the related-posts <div>.
    pat_related_heading = re.compile(
        r'\n*\s*<h2 id="related">[^<]*</h2>\s*' + related_div + r'\s*',
        re.DOTALL
    )
    # Pattern D: bare standalone related-posts div.
    pat_related_only = re.compile(
        r'\n*\s*' + related_div + r'\s*',
        re.DOTALL
    )
    # Pattern E: <h2 id="related"> heading followed by a plain <ul> of links
    # (markup used by ~5 older posts instead of the related-posts div).
    pat_related_ul = re.compile(
        r'\n*\s*<h2 id="related">[^<]*</h2>\s*'
        r'<ul>.*?</ul>\s*',
        re.DOTALL
    )
    # Pattern F: salvage for posts that got partially stripped by an earlier
    # (buggy) version of this function. The shape is:
    #   <ul class="related-list">…</ul>
    #   </div>   <-- orphan closer from the original outer related-posts div
    # We can safely remove both since neither has any remaining anchor.
    pat_orphan_related = re.compile(
        r'\n*\s*<ul class="related-list">.*?</ul>\s*</div>\s*',
        re.DOTALL
    )

    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        content = pat_share_buttons.sub('\n', content)
        content = pat_share_no_hr.sub('\n', content)
        content = pat_share_on_x.sub('\n', content)
        content = pat_related_heading.sub('\n', content)
        content = pat_related_only.sub('\n', content)
        content = pat_related_ul.sub('\n', content)
        content = pat_orphan_related.sub('\n', content)

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1

    return count


def fix_back_links(articles):
    """Move standalone back-link div into article-container so it aligns with body text."""
    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match the standalone back-link div (various style patterns)
        back_link_pattern = re.compile(
            r'<div style="max-width:\s*660px;[^"]*">\s*'
            r'<a [^>]*>&larr; Back to Posts</a>\s*'
            r'</div>',
            re.DOTALL
        )

        if not back_link_pattern.search(content):
            continue

        # Remove the standalone back-link div
        content = back_link_pattern.sub('', content)

        # Insert back link inside article-container, right before the <h1>
        back_link_html = (
            '<div style="margin-bottom:1.5rem;padding-top:1rem;">\n'
            '        <a href="/posts/" style="font-family:\'Inter\',-apple-system,system-ui,sans-serif;'
            'color:var(--text-muted);text-decoration:none;font-size:0.9rem;font-weight:500;">'
            '&larr; Back to Posts</a>\n'
            '    </div>\n        '
        )

        content = re.sub(
            r'(<article class="article-container">\s*)',
            r'\1' + back_link_html,
            content
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        count += 1

    return count


def inject_copy_link(articles):
    """Add a copy-link button below the TOC sidebar list."""
    COPY_LINK_MARKER = '<!-- COPY_LINK -->'
    COPY_LINK_HTML = (
        '<!-- COPY_LINK -->\n'
        '    <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--border);">\n'
        '        <button onclick="navigator.clipboard.writeText(window.location.href).then(()=>{const t=this.querySelector(\'span\');t.textContent=\'Copied!\';setTimeout(()=>t.textContent=\'Copy Link\',1500)})" '
        'style="display:inline-flex;align-items:center;gap:0.4rem;font-family:\'Inter\',-apple-system,system-ui,sans-serif;font-size:0.85rem;color:var(--text-muted);background:none;border:1px solid var(--border);border-radius:6px;padding:0.4rem 0.75rem;cursor:pointer;transition:color 0.2s,border-color 0.2s;" '
        'onmouseover="this.style.color=\'var(--text)\';this.style.borderColor=\'var(--text)\'" '
        'onmouseout="this.style.color=\'var(--text-muted)\';this.style.borderColor=\'var(--border)\'">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
        '</svg>'
        '<span>Copy Post Link</span></button>\n'
        '    </div>\n'
        '    <!-- /COPY_LINK -->'
    )

    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if already injected
        if COPY_LINK_MARKER in content:
            # Replace existing
            content = re.sub(
                r'<!-- COPY_LINK -->.*?<!-- /COPY_LINK -->',
                COPY_LINK_HTML,
                content,
                flags=re.DOTALL
            )
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
            continue

        # Insert before </aside> (end of toc-sidebar)
        if '</aside>' in content:
            content = content.replace(
                '</aside>',
                COPY_LINK_HTML + '\n</aside>',
                1
            )
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1

    return count


def strip_newsletter_redirect(articles):
    """Strip the legacy newsletter-redirect <script> block from every page.

    We used to inject a script that intercepted Substack form submits and
    redirected the main window to /subscribe/confirmed/. That whole flow is
    gone now — the homepage hosts Substack's official /embed iframe instead,
    which handles subscription inside the iframe without redirecting. The
    script is dead code; this function removes it across the repo.
    """
    # Sweep every static HTML page in the repo.
    article_paths = {a['filepath'] for a in articles}
    candidate_paths = list(article_paths)
    SKIP_DIRS = {'.git', '.wrangler', 'node_modules', '.claude'}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.html'):
                continue
            fp = os.path.join(dirpath, fn)
            if fp in article_paths:
                continue
            candidate_paths.append(fp)

    count = 0
    for filepath in candidate_paths:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if '<!-- NEWSLETTER_REDIRECT -->' not in content:
            continue
        new_content = re.sub(
            r'\n*<!-- NEWSLETTER_REDIRECT -->.*?<!-- /NEWSLETTER_REDIRECT -->\n*',
            '\n',
            content,
            flags=re.DOTALL,
        )
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            count += 1
    return count


# Hand-curated semantic neighbors per post (slug → list of 3 sibling slugs).
# These take precedence over the category-based fallback in pick_related().
# When adding a new post, either add an entry here (preferred) or let the
# category-based fallback pick siblings. The fallback is good enough that
# the site never ships without recommendations; this map exists so the
# recommendations feel intentional, not "3 most-recent unrelated posts".
CURATED_RELATED = {
    "posts/14x-ctr-gap": ["posts/stakes-priming", "posts/aeo-answer-engine-optimization", "posts/training-data-is-the-moat"],
    "posts/aeo-answer-engine-optimization": ["posts/training-data-is-the-moat", "posts/14x-ctr-gap", "posts/the-economics-of-the-internet-are-broken"],
    "posts/ai-comics-dos-donts": ["posts/ai-image-generation-comparison", "posts/nano-banana-vs-grok", "posts/wavespeed"],
    "posts/ai-image-generation-comparison": ["posts/nano-banana-vs-grok", "posts/ai-comics-dos-donts", "posts/wavespeed"],
    "posts/ai-music-generation-comparison": ["posts/ai-reels-what-actually-works", "posts/the-future-is-synthetic", "posts/wavespeed"],
    "posts/ai-psychosis": ["posts/human-in-the-loop", "posts/stakes-priming", "posts/openclaw-vs-claude-code-freedom"],
    "posts/ai-reels-what-actually-works": ["posts/best-ai-video-models", "posts/veo3-vs-hailuo-minimax", "posts/ai-music-generation-comparison"],
    "posts/ai-resilience-planning": ["posts/openclaw-claude-ban-ai-model-replacement", "posts/local-models-free-tokens", "posts/what-is-ai-self-healing"],
    "posts/best-ai-video-models": ["posts/veo3-vs-hailuo-minimax", "posts/ai-reels-what-actually-works", "posts/wavespeed"],
    "posts/build-for-agents-price-per-call": ["posts/veracity-postmortem", "posts/future-of-software-is-headless", "posts/the-economics-of-the-internet-are-broken"],
    "posts/future-of-content-agentic-data-enrichment": ["posts/training-data-is-the-moat", "posts/aeo-answer-engine-optimization", "posts/the-future-is-synthetic"],
    "posts/future-of-software-is-headless": ["posts/build-for-agents-price-per-call", "posts/the-great-api-shutdown", "posts/the-economics-of-the-internet-are-broken"],
    "posts/google-zero-patience-ai-slop": ["posts/scaling-ai-is-lazy", "posts/what-is-ai-drift-how-to-fix", "posts/aeo-answer-engine-optimization"],
    "posts/kapiko-postmortem": ["posts/palmaura-postmortem", "posts/veracity-postmortem", "posts/ai-music-generation-comparison"],
    "posts/palmaura-postmortem": ["posts/kapiko-postmortem", "posts/veracity-postmortem", "posts/plan-3x-build-once"],
    "posts/veracity-postmortem": ["posts/build-for-agents-price-per-call", "posts/kapiko-postmortem", "posts/palmaura-postmortem"],
    "posts/tabiji-18m-views": ["posts/how-my-agent-made-a-viral-video", "posts/true-cost-of-ai-content-production", "posts/kapiko-postmortem"],
    "posts/how-my-agent-made-a-viral-video": ["posts/tabiji-18m-views", "posts/true-cost-of-ai-content-production", "posts/kapiko-postmortem"],
    "posts/may-2026-recap": ["posts/back-to-the-tables", "posts/plan-3x-build-once", "posts/tabiji-18m-views"],
    "posts/human-in-the-loop": ["posts/ai-psychosis", "posts/openclaw-vs-claude-code-freedom", "posts/stop-optimizing-ai-infrastructure"],
    "posts/local-models-free-tokens": ["posts/ai-resilience-planning", "posts/openclaw-vs-claude-code-freedom", "posts/build-for-agents-price-per-call"],
    "posts/makeugc": ["posts/wavespeed", "posts/ai-reels-what-actually-works", "posts/veo3-vs-hailuo-minimax"],
    "posts/nano-banana-vs-grok": ["posts/ai-image-generation-comparison", "posts/ai-comics-dos-donts", "posts/wavespeed"],
    "posts/openclaw-claude-ban-ai-model-replacement": ["posts/ai-resilience-planning", "posts/openclaw-vs-claude-code-freedom", "posts/openclaw-skill-tree"],
    "posts/openclaw-skill-tree": ["posts/openclaw-vs-claude-code-freedom", "posts/openclaw-claude-ban-ai-model-replacement", "posts/stop-optimizing-ai-infrastructure"],
    "posts/openclaw-vs-claude-code-freedom": ["posts/openclaw-skill-tree", "posts/openclaw-claude-ban-ai-model-replacement", "posts/build-for-agents-price-per-call"],
    "posts/devil-is-in-the-ai-skills": ["posts/openclaw-skill-tree", "posts/build-for-agents-price-per-call", "posts/plan-3x-build-once"],
    "posts/every-ai-is-intj": ["posts/ai-attachment-secure", "posts/ai-disc-c-dominant", "posts/ai-enneagram-different-types"],
    "posts/three-of-four-ais-same-person": ["posts/ai-attachment-secure", "posts/ai-disc-c-dominant", "posts/ai-enneagram-different-types"],
    "posts/ai-enneagram-different-types": ["posts/ai-attachment-secure", "posts/ai-disc-c-dominant", "posts/three-of-four-ais-same-person"],
    "posts/ai-disc-c-dominant": ["posts/ai-attachment-secure", "posts/ai-enneagram-different-types", "posts/three-of-four-ais-same-person"],
    "posts/ai-attachment-secure": ["posts/ai-disc-c-dominant", "posts/ai-enneagram-different-types", "posts/three-of-four-ais-same-person"],
    "posts/plan-3x-build-once": ["posts/stakes-priming", "posts/build-for-agents-price-per-call", "posts/openclaw-vs-claude-code-freedom"],
    "posts/rise-of-the-ai-influencer": ["posts/the-future-is-synthetic", "posts/slop-iterate-curate-ai-content", "posts/true-cost-of-ai-content-production"],
    "posts/scaling-ai-is-lazy": ["posts/what-is-ai-reward-hacking", "posts/what-is-ai-drift-how-to-fix", "posts/google-zero-patience-ai-slop"],
    "posts/slop-iterate-curate-ai-content": ["posts/true-cost-of-ai-content-production", "posts/ai-reels-what-actually-works", "posts/the-future-is-synthetic"],
    "posts/stakes-priming": ["posts/stakes-priming-surface-area", "posts/ai-psychosis", "posts/what-is-ai-reward-hacking"],
    "posts/stakes-priming-surface-area": ["posts/stakes-priming", "posts/what-is-ai-reward-hacking", "posts/ai-psychosis"],
    "posts/retiring-autonomous-agent-paper-fund-ii": ["posts/introducing-autonomous-agent-paper-fund-ii-psy", "posts/autonomous-trading-crons-retrospective", "posts/introducing-autonomous-agent-paper-fund-i-slo"],
    "posts/autonomous-trading-crons-retrospective": ["posts/introducing-autonomous-agent-paper-fund-i-slo", "posts/retiring-autonomous-agent-paper-fund-ii", "posts/sol-fund-revision-c-contamination-lesson"],
    "posts/introducing-autonomous-agent-paper-fund-ii-psy": ["posts/retiring-autonomous-agent-paper-fund-ii", "posts/introducing-autonomous-agent-paper-fund-i-slo", "posts/autonomous-trading-crons-retrospective"],
    "posts/introducing-autonomous-agent-paper-fund-i-slo": ["posts/autonomous-trading-crons-retrospective", "posts/retiring-autonomous-agent-paper-fund-ii", "posts/introducing-autonomous-agent-paper-fund-ii-psy"],
    "posts/persistent-ai-agents": ["posts/ai-trading-rig", "posts/human-in-the-loop", "posts/where-ai-personalities-come-from"],
    "posts/ai-trading-rig": ["posts/ai-desk-figr-earnings", "posts/retiring-autonomous-agent-paper-fund-ii", "posts/autonomous-trading-crons-retrospective"],
    "posts/ai-desk-figr-earnings": ["posts/ai-trading-rig", "posts/vibe-trading", "posts/autonomous-trading-crons-retrospective"],
    "posts/vibe-trading": ["posts/introducing-autonomous-agent-paper-fund-i-slo", "posts/introducing-autonomous-agent-paper-fund-ii-psy", "posts/google-trends-stock-attention"],
    "posts/google-trends-stock-attention": ["posts/vibe-trading", "posts/trade-log-2026-07-22", "posts/back-to-the-tables"],
    "posts/i-trained-a-gpt-on-my-life": ["posts/inside-ai-training-data", "posts/where-ai-personalities-come-from", "posts/every-ai-is-intj"],
    "posts/inside-ai-training-data": ["posts/watching-ai-learn-paris", "posts/where-ai-personalities-come-from", "posts/i-trained-a-gpt-on-my-life"],
    "posts/agentic-rails": ["posts/devil-is-in-the-ai-skills", "posts/plan-3x-build-once", "posts/ai-resilience-planning"],
    "posts/where-ai-personalities-come-from": ["posts/inside-ai-training-data", "posts/i-trained-a-gpt-on-my-life", "posts/every-ai-is-intj"],
    "posts/pixelforge-launch": ["posts/plan-3x-build-once", "posts/stakes-priming-surface-area", "posts/kapiko-postmortem"],
    "posts/back-to-the-tables": ["posts/vibe-trading", "posts/may-2026-recap", "posts/pixelforge-launch"],
    "posts/stop-optimizing-ai-infrastructure": ["posts/agentic-rails", "posts/openclaw-skill-tree", "posts/human-in-the-loop"],
    "posts/nothing-looked-wrong": ["posts/mdb-option-expiry-date-risk", "posts/ai-desk-figr-earnings", "posts/ai-trading-rig"],
    "posts/sol-fund-winning-strategies-vs-qqq-spy": ["posts/sol-fund-revision-c-contamination-lesson", "posts/vibe-trading", "posts/autonomous-trading-crons-retrospective"],
    "posts/sol-fund-revision-c-contamination-lesson": ["posts/sol-fund-winning-strategies-vs-qqq-spy", "posts/autonomous-trading-crons-retrospective", "posts/vibe-trading"],
    "posts/i-analyzed-every-token-launch": ["posts/13f-congress-trade-data-lag", "posts/google-trends-stock-attention", "posts/ai-trading-rig"],
    "posts/mdb-option-expiry-date-risk": ["posts/nothing-looked-wrong", "posts/trade-log-2026-07-24", "posts/ai-desk-figr-earnings"],
    "posts/watching-ai-learn-paris": ["posts/inside-ai-training-data", "posts/where-ai-personalities-come-from", "posts/i-trained-a-gpt-on-my-life"],
    "posts/13f-congress-trade-data-lag": ["posts/google-trends-stock-attention", "posts/i-analyzed-every-token-launch", "posts/ai-desk-figr-earnings"],
    "posts/trade-log-2026-07-24": ["posts/mdb-option-expiry-date-risk", "posts/trade-log-2026-07-22", "posts/ai-desk-figr-earnings"],
    "posts/trade-log-2026-07-22": ["posts/trade-log-2026-07-24", "posts/mdb-option-expiry-date-risk", "posts/google-trends-stock-attention"],
    "posts/the-economics-of-the-internet-are-broken": ["posts/the-great-api-shutdown", "posts/aeo-answer-engine-optimization", "posts/build-for-agents-price-per-call"],
    "posts/the-future-is-synthetic": ["posts/rise-of-the-ai-influencer", "posts/slop-iterate-curate-ai-content", "posts/future-of-content-agentic-data-enrichment"],
    "posts/the-great-api-shutdown": ["posts/the-economics-of-the-internet-are-broken", "posts/future-of-software-is-headless", "posts/aeo-answer-engine-optimization"],
    "posts/training-data-is-the-moat": ["posts/aeo-answer-engine-optimization", "posts/future-of-content-agentic-data-enrichment", "posts/the-economics-of-the-internet-are-broken"],
    "posts/true-cost-of-ai-content-production": ["posts/slop-iterate-curate-ai-content", "posts/scaling-ai-is-lazy", "posts/the-future-is-synthetic"],
    "posts/veo3-vs-hailuo-minimax": ["posts/best-ai-video-models", "posts/ai-reels-what-actually-works", "posts/wavespeed"],
    "posts/wavespeed": ["posts/makeugc", "posts/veo3-vs-hailuo-minimax", "posts/best-ai-video-models"],
    "posts/what-is-ai-drift-how-to-fix": ["posts/what-is-ai-reward-hacking", "posts/what-is-ai-self-healing", "posts/scaling-ai-is-lazy"],
    "posts/what-is-ai-reward-hacking": ["posts/what-is-ai-drift-how-to-fix", "posts/what-is-ai-self-healing", "posts/scaling-ai-is-lazy"],
    "posts/what-is-ai-self-healing": ["posts/what-is-ai-reward-hacking", "posts/what-is-ai-drift-how-to-fix", "posts/ai-resilience-planning"],
}


def pick_related(article, articles, n=3):
    """Pick n related articles.

    Order of preference:
      1. CURATED_RELATED map (hand-curated semantic neighbors). When a slug
         appears in the curated map, use that list directly — the curation
         was done with knowledge of every post's topic, not just category.
      2. Same-category siblings, ordered by recency (articles is already
         sorted newest-first).
      3. Most-recent overall, to fill remaining slots.

    Excludes the current article. Excludes curated targets that no longer
    exist on disk (so renaming a post fails-soft).
    """
    by_slug = {a['slug']: a for a in articles}

    # 1. Curated map
    curated = CURATED_RELATED.get(article['slug'], [])
    selected = []
    seen = set()
    for slug in curated:
        if slug == article['slug'] or slug in seen:
            continue
        candidate = by_slug.get(slug)
        if candidate is None:
            continue
        selected.append(candidate)
        seen.add(slug)
        if len(selected) == n:
            return selected

    # 2 + 3. Fallback: same-category by recency, then everything else by recency.
    others = [a for a in articles if a['slug'] != article['slug'] and a['slug'] not in seen]
    same_cat = [a for a in others if a['category'] == article['category']]
    rest = [a for a in others if a['category'] != article['category']]
    for a in same_cat + rest:
        if a['slug'] in seen:
            continue
        seen.add(a['slug'])
        selected.append(a)
        if len(selected) == n:
            break
    return selected


def render_recommended_block(items):
    """Render the markered <section> for n recommended posts."""
    rows = []
    for item in items:
        slug = item['slug']
        title = html.escape(item['title'])
        desc = html.escape(item.get('description', '') or '')
        # Trim long descriptions to avoid a wall-of-text recommendation list.
        if len(desc) > 160:
            desc = desc[:157].rsplit(' ', 1)[0] + '…'
        rows.append(
            f'                <li>'
            f'<a class="zn-recommended-title" href="/{slug}/">{title}</a>'
            f'<p class="zn-recommended-dek">{desc}</p>'
            f'</li>'
        )

    return (
        '<!-- RECOMMENDED_START -->\n'
        '            <section class="zn-recommended" id="related">\n'
        '                <p class="zn-recommended-label">Recommended Reading</p>\n'
        '                <ul class="zn-recommended-list">\n'
        + '\n'.join(rows) + '\n'
        '                </ul>\n'
        '            </section>\n'
        '            <!-- RECOMMENDED_END -->'
    )


def find_article_body_close(content):
    """Find the </div> position that closes <div class="article-body">.

    Returns (start_index, end_index) of the closing </div>, or None.
    Uses a depth counter rather than a regex so it handles arbitrary nesting
    of <div> and <figure>/<section>/etc. (only counts <div>).
    """
    start = content.find('<div class="article-body">')
    if start == -1:
        return None
    pos = start + len('<div class="article-body">')
    depth = 1
    while depth > 0:
        nxt_open = content.find('<div', pos)
        nxt_close = content.find('</div>', pos)
        if nxt_close == -1:
            return None
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            pos = nxt_open + 4
        else:
            depth -= 1
            if depth == 0:
                return (nxt_close, nxt_close + len('</div>'))
            pos = nxt_close + len('</div>')
    return None


def inject_post_subscribe(articles):
    """Add (or refresh) the post-end Substack subscribe block on every article.

    Sits between the article body and the Recommended Reading block. Uses
    Substack's transparent embed and the wrapper-crop trick to hide the
    disclaimer + logo (same approach as the homepage instance).

    Idempotent — finds existing markers and replaces between them. If no
    markers yet, prefers inserting BEFORE the recommended-reading block; if
    that also doesn't exist, falls back to right after the article-body close.
    """
    BLOCK = (
        '<!-- SUBSCRIBE_BLOCK_START -->\n'
        '            <section class="zn-post-subscribe">\n'
        '                <p class="zn-post-subscribe-label">Newsletter</p>\n'
        '                <h2 class="zn-post-subscribe-headline">Get the next post by email.</h2>\n'
        '                <p class="zn-post-subscribe-sub">One email when I publish something new. No spam, no fixed schedule, unsubscribe anytime.</p>\n'
        '                <form class="zn-subscribe-form zn-post-subscribe-form" data-resend-subscribe novalidate>\n'
        '                    <input type="email" name="email" placeholder="your@email.com" required aria-label="Email address" autocomplete="email">\n'
        '                    <button type="submit">Subscribe &rarr;</button>\n'
        '                    <p class="zn-subscribe-status" data-subscribe-status hidden></p>\n'
        '                </form>\n'
        '            </section>\n'
        '            <!-- SUBSCRIBE_BLOCK_END -->'
    )

    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        if '<!-- SUBSCRIBE_BLOCK_START -->' in content and '<!-- SUBSCRIBE_BLOCK_END -->' in content:
            content = re.sub(
                r'<!-- SUBSCRIBE_BLOCK_START -->.*?<!-- SUBSCRIBE_BLOCK_END -->',
                lambda m: BLOCK,
                content,
                flags=re.DOTALL,
            )
        elif '<!-- RECOMMENDED_START -->' in content:
            # Insert before the recommended-reading block.
            content = content.replace(
                '<!-- RECOMMENDED_START -->',
                BLOCK + '\n        <!-- RECOMMENDED_START -->',
                1,
            )
        else:
            close = find_article_body_close(content)
            if close is None:
                continue
            insert_at = close[1]
            content = content[:insert_at] + '\n        ' + BLOCK + content[insert_at:]

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
    return count


def inject_recommended_reading(articles):
    """Add (or refresh) a 3-item Recommended Reading block at the end of each
    article body. Idempotent — finds existing markers and replaces between
    them, otherwise inserts before the article-body's closing </div>.
    """
    count = 0
    for article in articles:
        related = pick_related(article, articles, n=3)
        if len(related) < 3:
            # Need at least 3 others to ship the block.
            continue
        block = render_recommended_block(related)

        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content

        if '<!-- RECOMMENDED_START -->' in content and '<!-- RECOMMENDED_END -->' in content:
            content = re.sub(
                r'<!-- RECOMMENDED_START -->.*?<!-- RECOMMENDED_END -->',
                lambda m: block,
                content,
                flags=re.DOTALL,
            )
        else:
            close = find_article_body_close(content)
            if close is None:
                continue
            # Insert AFTER the </div> that closes <div class="article-body">,
            # so the section is a peer of the body (and not affected by
            # .article-body descendant CSS in per-page inline styles).
            insert_at = close[1]
            content = content[:insert_at] + '\n        ' + block + content[insert_at:]

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Post <head>, JSON-LD normalization, and Markdown mirror generation
# ---------------------------------------------------------------------------

AUTHOR_SAME_AS = [
    "https://x.com/bernardjhuang",
    "https://www.linkedin.com/in/bernardjhuang/",
    "https://github.com/bernardjhuang",
]


def _extract_article_body_html(content):
    """Return the inner HTML of <div class="article-body"> without footer/subscribe/related chrome."""
    start = content.find('<div class="article-body">')
    if start == -1:
        return ''
    inner_start = start + len('<div class="article-body">')
    close = find_article_body_close(content)
    body = content[inner_start:close[0]] if close else content[inner_start:]
    body = re.sub(r'<!-- SUBSCRIBE_BLOCK_START -->.*?<!-- SUBSCRIBE_BLOCK_END -->', '', body, flags=re.DOTALL)
    body = re.sub(r'<!-- RECOMMENDED_START -->.*?<!-- RECOMMENDED_END -->', '', body, flags=re.DOTALL)
    return body


def compute_word_count(content):
    """Word count of clean editorial prose inside <div class="article-body">."""
    body = _extract_article_body_html(content)
    if not body:
        return 0
    clean = re.sub(r'<svg\b[^>]*>.*?</svg>', ' ', body, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r'<!--.*?-->', ' ', clean, flags=re.DOTALL)
    txt = _strip_tags_clean(clean)
    return len(re.findall(r"\b[\w'’-]+\b", txt))


def _extract_author_from_html(content):
    """Return display author string from Article JSON-LD (default: Bernard Huang)."""
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get('@type') in ('Article', 'BlogPosting', 'TechArticle'):
                auth = item.get('author')
                if isinstance(auth, dict) and auth.get('name'):
                    return auth['name']
                if isinstance(auth, list):
                    names = [x.get('name') for x in auth if isinstance(x, dict) and x.get('name')]
                    if names:
                        return ', '.join(names)
    return 'Bernard Huang'


def sync_post_seo_metadata(articles):
    """Idempotently normalize <head> social/discovery tags and enrich Article JSON-LD."""
    count = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original = content
        slug = article['slug']
        canonical_url = f'{SITE_URL}/{slug}/'
        md_url = f'{SITE_URL}/{slug}/index.md'
        mod_date = article.get('modified_date') or article.get('date') or ''
        word_count = compute_word_count(content)

        # Split head and rest so we only normalize <head> metadata/JSON-LD
        head_m = re.search(r'(<head[^>]*>)(.*?)(</head>)', content, re.DOTALL | re.IGNORECASE)
        if not head_m:
            continue
        head_open, head_inner, head_close = head_m.group(1), head_m.group(2), head_m.group(3)

        # 1. Upgrade twitter:card summary -> summary_large_image
        if re.search(r'<meta\s+name=["\']twitter:card["\']', head_inner, re.IGNORECASE):
            head_inner = re.sub(
                r'(<meta\s+name=["\']twitter:card["\']\s+content=)(["\'])summary\2',
                r'\1\2summary_large_image\2',
                head_inner,
                flags=re.IGNORECASE,
            )
        else:
            head_inner = head_inner.rstrip() + '\n    <meta name="twitter:card" content="summary_large_image">\n'

        # 2. Ensure og:site_name
        if not re.search(r'property=["\']og:site_name["\']', head_inner, re.IGNORECASE):
            if re.search(r'<meta\s+property=["\']og:title["\']', head_inner, re.IGNORECASE):
                head_inner = re.sub(
                    r'(\s*<meta\s+property=["\']og:title["\'])',
                    '\n    <meta property="og:site_name" content="Zonted">\\1',
                    head_inner,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                head_inner = head_inner.rstrip() + '\n    <meta property="og:site_name" content="Zonted">\n'

        # 3. Ensure article:modified_time
        if mod_date and not re.search(r'property=["\']article:modified_time["\']', head_inner, re.IGNORECASE):
            if re.search(r'<meta\s+property=["\']article:published_time["\'][^>]*>', head_inner, re.IGNORECASE):
                head_inner = re.sub(
                    r'(<meta\s+property=["\']article:published_time["\'][^>]*>)',
                    f'\\1\n    <meta property="article:modified_time" content="{mod_date}">',
                    head_inner,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                head_inner = head_inner.rstrip() + f'\n    <meta property="article:modified_time" content="{mod_date}">\n'

        # 4. Ensure <link rel="alternate"> for llms.txt and index.md
        if 'https://zonted.com/llms.txt' not in head_inner:
            if re.search(r'<link\s+rel=["\']alternate["\'][^>]*feed\.xml["\'][^>]*>', head_inner, re.IGNORECASE):
                head_inner = re.sub(
                    r'(<link\s+rel=["\']alternate["\'][^>]*feed\.xml["\'][^>]*>)',
                    '\\1\n    <link rel="alternate" type="text/plain" title="LLMs.txt" href="https://zonted.com/llms.txt">',
                    head_inner,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                head_inner = head_inner.rstrip() + '\n    <link rel="alternate" type="text/plain" title="LLMs.txt" href="https://zonted.com/llms.txt">\n'

        if md_url not in head_inner:
            head_inner = re.sub(
                r'(<link\s+rel=["\']alternate["\'][^>]*llms\.txt["\'][^>]*>)',
                f'\\1\n    <link rel="alternate" type="text/markdown" title="Markdown version" href="{md_url}">',
                head_inner,
                count=1,
                flags=re.IGNORECASE,
            )

        # 5. Unpack array-wrapped JSON-LD & enrich Article schema non-destructively
        def _rewrite_ld(match):
            raw = match.group(1).strip()
            try:
                parsed = json.loads(raw)
            except Exception:
                return match.group(0)

            was_list = isinstance(parsed, list)
            items = parsed if was_list else [parsed]
            new_items = []
            changed = was_list

            for item in items:
                if isinstance(item, dict) and item.get('@type') in ('Article', 'BlogPosting', 'TechArticle'):
                    before = json.dumps(item, sort_keys=True)
                    if mod_date and 'dateModified' not in item:
                        item['dateModified'] = mod_date
                    if 'mainEntityOfPage' not in item:
                        item['mainEntityOfPage'] = {'@type': 'WebPage', '@id': canonical_url}
                    item['inLanguage'] = 'en-US'
                    if word_count > 0:
                        item['wordCount'] = word_count
                    item['articleSection'] = article['category']
                    item['speakable'] = {
                        '@type': 'SpeakableSpecification',
                        'cssSelector': ['.article-container h1', '.tldr'],
                    }
                    pub = item.get('publisher')
                    if not isinstance(pub, dict) or (pub.get('name') == 'Zonted' and '@id' not in pub):
                        item['publisher'] = {
                            '@type': 'Organization',
                            '@id': f'{SITE_URL}/#organization',
                            'name': 'Zonted',
                            'url': f'{SITE_URL}/',
                        }
                    auth = item.get('author')
                    if isinstance(auth, dict) and auth.get('name') == 'Bernard Huang':
                        auth['@id'] = f'{SITE_URL}/#bernard-huang'
                        auth.setdefault('url', f'{SITE_URL}/about/')
                        auth.setdefault('sameAs', AUTHOR_SAME_AS)
                    if json.dumps(item, sort_keys=True) != before:
                        changed = True
                new_items.append(item)

            if not changed:
                return match.group(0)

            blocks = [
                f'<script type="application/ld+json">\n    {json.dumps(obj, ensure_ascii=False)}\n    </script>'
                for obj in new_items
            ]
            return '\n    '.join(blocks)

        head_inner = re.sub(
            r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>',
            _rewrite_ld,
            head_inner,
            flags=re.DOTALL | re.IGNORECASE,
        )

        content = content[:head_m.start()] + head_open + head_inner + head_close + content[head_m.end():]
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            count += 1
    return count


class _ArticleMarkdownParser(HTMLParser):
    """Convert Zonted post .article-body HTML into clean, agent-readable Markdown."""

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.out = []
        self.skip_stack = []
        self.in_pre = False
        self.code_buf = None
        self.link_stack = []
        self.list_stack = []
        self.fmt_stack = []
        self.in_blockquote = False
        self.bq_buf = None
        self.in_table = False
        self.table_rows = []
        self.cur_row = None
        self.cur_cell = None
        self.in_figcaption = False
        self.tldr_label_tag = None

    def _emit(self, text):
        if self.skip_stack:
            return
        if self.fmt_stack:
            self.fmt_stack[-1][1].append(text)
        elif self.in_table and self.cur_cell is not None:
            self.cur_cell.append(text)
        elif self.in_blockquote and self.bq_buf is not None:
            self.bq_buf.append(text)
        elif self.code_buf is not None:
            self.code_buf.append(text)
        else:
            self.out.append(text)

    def _flush_fmt_until(self, marker):
        for i in range(len(self.fmt_stack) - 1, -1, -1):
            if self.fmt_stack[i][0] == marker:
                _, buf = self.fmt_stack.pop(i)
                raw = ''.join(buf)
                inner = raw.strip()
                if inner:
                    lead = ' ' if raw[:1].isspace() else ''
                    trail = ' ' if raw[-1:].isspace() else ''
                    self._emit(f'{lead}{marker}{inner}{marker}{trail}')
                elif raw:
                    self._emit(' ')
                break

    def _resolve_url(self, u):
        if not u:
            return ''
        u = u.strip()
        if u.startswith(('http://', 'https://', 'mailto:', '#', 'data:')):
            return u
        if u.startswith('/'):
            return SITE_URL + u
        return urljoin(self.base_url, u)

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr = dict(attrs)
        if self.skip_stack:
            if tag in ('svg', 'script', 'style', 'form', 'button'):
                self.skip_stack.append(tag)
            return
        if tag in ('svg', 'script', 'style', 'form', 'button', 'input'):
            if tag != 'input':
                self.skip_stack.append(tag)
            return

        cls_tokens = attr.get('class', '').split()
        if 'tldr-label' in cls_tokens:
            self.tldr_label_tag = tag
            self._emit('\n\n## ')
            return

        if tag in ('h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self._emit('\n\n' + '#' * level + ' ')
        elif tag == 'p':
            if self.list_stack:
                self._emit('')
            else:
                self._emit('\n\n')
        elif tag == 'br':
            self._emit('  \n')
        elif tag == 'hr':
            self._emit('\n\n---\n\n')
        elif tag == 'blockquote':
            self.in_blockquote = True
            self.bq_buf = []
        elif tag == 'pre':
            self.in_pre = True
            self.code_buf = []
        elif tag == 'code':
            if not self.in_pre:
                self._emit('`')
        elif tag in ('strong', 'b'):
            self.fmt_stack.append(('**', []))
        elif tag in ('em', 'i'):
            if not self.in_figcaption:
                self.fmt_stack.append(('*', []))
        elif tag == 'a':
            href = self._resolve_url(attr.get('href', ''))
            self.link_stack.append(href)
            self._emit('[')
        elif tag == 'ul':
            self.list_stack.append(['ul', 0])
            if len(self.list_stack) == 1:
                self._emit('\n\n')
        elif tag == 'ol':
            self.list_stack.append(['ol', 0])
            if len(self.list_stack) == 1:
                self._emit('\n\n')
        elif tag == 'li':
            indent = '  ' * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1][0] == 'ol':
                self.list_stack[-1][1] += 1
                self._emit(f'\n{indent}{self.list_stack[-1][1]}. ')
            else:
                self._emit(f'\n{indent}- ')
        elif tag == 'img':
            src = self._resolve_url(attr.get('src', ''))
            alt = re.sub(r'\s+', ' ', (attr.get('alt') or '')).strip().replace(']', '\\]')
            if src:
                self._emit(f'\n\n![{alt}]({src})\n')
        elif tag == 'figcaption':
            self.in_figcaption = True
            self._emit('\n*')
        elif tag == 'summary':
            self._emit('\n\n**')
        elif tag == 'table':
            self.in_table = True
            self.table_rows = []
        elif tag == 'tr' and self.in_table:
            self.cur_row = []
        elif tag in ('th', 'td') and self.in_table:
            self.cur_cell = []
        elif tag in ('video', 'audio', 'iframe'):
            src = self._resolve_url(attr.get('src', ''))
            if src:
                label = 'Video' if tag == 'video' else ('Audio' if tag == 'audio' else 'Embedded media')
                self._emit(f'\n\n[{label}]({src})\n')
        elif tag == 'source':
            src = self._resolve_url(attr.get('src', ''))
            if src:
                self._emit(f'\n\n[Media]({src})\n')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return
        if self.tldr_label_tag and tag == self.tldr_label_tag:
            self.tldr_label_tag = None
            self._emit('\n\n')
            return
        if tag in ('h2', 'h3', 'h4', 'h5', 'h6'):
            self._emit('\n\n')
        elif tag == 'p':
            self._emit('\n\n')
        elif tag == 'blockquote' and self.in_blockquote:
            while self.fmt_stack:
                self._flush_fmt_until(self.fmt_stack[-1][0])
            raw = ''.join(self.bq_buf).strip()
            self.in_blockquote = False
            self.bq_buf = None
            if raw:
                lines = [f'> {ln}' if ln.strip() else '>' for ln in raw.splitlines()]
                self._emit('\n\n' + '\n'.join(lines) + '\n\n')
        elif tag == 'pre':
            raw = ''.join(self.code_buf or []).strip('\n')
            self.in_pre = False
            self.code_buf = None
            self._emit(f'\n\n```\n{raw}\n```\n\n')
        elif tag == 'code':
            if not self.in_pre:
                self._emit('`')
        elif tag in ('strong', 'b'):
            self._flush_fmt_until('**')
        elif tag in ('em', 'i'):
            if not self.in_figcaption:
                self._flush_fmt_until('*')
        elif tag == 'a':
            href = self.link_stack.pop() if self.link_stack else ''
            self._emit(f']({href})' if href else ']')
        elif tag in ('ul', 'ol'):
            if self.list_stack:
                self.list_stack.pop()
            self._emit('\n\n')
        elif tag == 'figcaption':
            self.in_figcaption = False
            self._emit('*\n\n')
        elif tag == 'summary':
            self._emit('**\n\n')
        elif tag in ('th', 'td') and self.in_table and self.cur_row is not None and self.cur_cell is not None:
            while self.fmt_stack:
                self._flush_fmt_until(self.fmt_stack[-1][0])
            cell_txt = re.sub(r'\s+', ' ', ''.join(self.cur_cell)).strip().replace('|', '\\|')
            self.cur_row.append((tag, cell_txt))
            self.cur_cell = None
        elif tag == 'tr' and self.in_table and self.cur_row is not None:
            if self.cur_row:
                self.table_rows.append(self.cur_row)
            self.cur_row = None
        elif tag == 'table' and self.in_table:
            rows = self.table_rows
            self.in_table = False
            self.table_rows = []
            if rows:
                ncols = max(len(r) for r in rows)
                norm = [[c[1] for c in r] + [''] * (ncols - len(r)) for r in rows]
                lines = ['| ' + ' | '.join(norm[0]) + ' |', '| ' + ' | '.join(['---'] * ncols) + ' |']
                for r in norm[1:]:
                    lines.append('| ' + ' | '.join(r) + ' |')
                self._emit('\n\n' + '\n'.join(lines) + '\n\n')

    def handle_data(self, data):
        if self.skip_stack:
            return
        if self.in_pre:
            self._emit(data)
            return
        collapsed = re.sub(r'[ \t\r\n]+', ' ', data)
        self._emit(collapsed)


def _html_to_markdown(body_html, base_url):
    parser = _ArticleMarkdownParser(base_url)
    parser.feed(body_html)
    parser.close()
    md = ''.join(parser.out)
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\n[ \t]+(?![-*0-9> ])', '\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()


def generate_markdown_mirrors(articles):
    """Write clean, zero-boilerplate Markdown mirrors at posts/<slug>/index.md."""
    written = 0
    for article in articles:
        filepath = article['filepath']
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        slug = article['slug']
        canonical_url = f'{SITE_URL}/{slug}/'
        author = _extract_author_from_html(content)
        date_str = article.get('date') or ''
        mod_date = article.get('modified_date') or date_str
        body_html = _extract_article_body_html(content)
        body_md = _html_to_markdown(body_html, canonical_url)

        fm = [
            '---',
            f'title: {json.dumps(article["h1"] or article["title"], ensure_ascii=False)}',
            f'author: {json.dumps(author, ensure_ascii=False)}',
            f'date: {json.dumps(date_str)}',
            f'modified: {json.dumps(mod_date)}',
            f'canonical: {json.dumps(canonical_url)}',
            f'category: {json.dumps(article["category"], ensure_ascii=False)}',
            f'description: {json.dumps(article.get("description") or "", ensure_ascii=False)}',
            '---',
            '',
            f'# {article["h1"] or article["title"]}',
            '',
            f'By {author} · {date_str}' + (f' · {article["reading_time"]} min read' if article.get('reading_time') else ''),
            '',
            body_md,
            '',
        ]
        out_text = '\n'.join(fm)
        md_path = os.path.join(os.path.dirname(filepath), 'index.md')
        existing = None
        if os.path.isfile(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                existing = f.read()
        if existing != out_text:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(out_text)
            written += 1
    return written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    articles = scan_articles()
    print(f"Found {len(articles)} articles")

    n = strip_nav_links(articles)
    print(f"Stripped nav links from {n} articles")

    n = strip_share_and_related(articles)
    print(f"Stripped share + Keep Reading blocks from {n} articles")

    n = fix_back_links(articles)
    print(f"Fixed back link alignment in {n} articles")

    n = inject_copy_link(articles)
    print(f"Injected copy-link button into {n} articles")

    n = strip_newsletter_redirect(articles)
    print(f"Stripped legacy newsletter-redirect script from {n} files")

    n = inject_post_subscribe(articles)
    print(f"Injected post-end subscribe block into {n} articles")

    n = inject_recommended_reading(articles)
    print(f"Injected Recommended Reading block into {n} articles")

    n = sync_post_seo_metadata(articles)
    print(f"Synchronized SEO metadata & JSON-LD in {n} articles")

    # Re-scan after metadata sync so sitemap/llms reflect synced modified dates
    articles = scan_articles()

    n = generate_homepage(articles)
    print(f"Generated index.html ({n} entries)")

    n = generate_posts_hub(articles)
    print(f"Generated posts/index.html ({n} entries)")

    n = generate_sitemap(articles)
    print(f"Generated sitemap.xml ({n} URLs)")

    n = generate_feed(articles)
    print(f"Generated feed.xml ({n} items)")

    n = generate_markdown_mirrors(articles)
    print(f"Generated Markdown mirrors ({n} updated)")

    n = generate_llms(articles)
    print(f"Generated llms.txt + llms-full.txt ({n} posts)")


if __name__ == '__main__':
    main()
