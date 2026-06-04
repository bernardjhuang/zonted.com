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
from datetime import datetime

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
    "posts/stakes-priming": "/posts/stakes-priming/img/tabiji-verdict.png",
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
    if 'review' in slug_lower:
        return 'Reviews'
    if any(w in title_lower for w in ['vs', 'comparison', 'compared', 'showdown', 'best ai']):
        return 'Comparisons'
    if any(w in title_lower for w in ['what is', 'how to', 'guide', 'planning']):
        return 'Guides'
    if any(w in title_lower for w in ['reels', 'instagram', 'youtube', 'tiktok', 'short-form', 'video services']):
        return 'Production'
    return 'Opinion'


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
        'description': description,
        'date': date_str,
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
                meta['_mtime'] = os.path.getmtime(index_file)
                articles.append(meta)

    # Sort by date (newest first), tie-break by file mtime so two posts that
    # publish on the same calendar day order by which was written most
    # recently (instead of by os.listdir() filesystem order, which is
    # undefined). Articles without dates go last.
    articles.sort(key=lambda a: (a['date'] or '0000-00-00', a.get('_mtime', 0)), reverse=True)
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

def generate_sitemap(articles):
    today = datetime.now().strftime('%Y-%m-%d')
    urls = []

    # Homepage
    urls.append(('/', '1.0', today))
    # Hubs
    urls.append(('/posts/', '0.8', today))
    urls.append(('/portfolio/', '0.8', today))
    urls.append(('/ai-stack/', '0.8', today))
    urls.append(('/metrics/', '0.7', today))
    # About
    urls.append(('/about/', '0.6', today))

    # Articles
    for a in articles:
        lastmod = a['date'] or today
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

def generate_feed(articles):
    items = []
    for a in articles:
        pub_date = format_date_rfc822(a['date']) if a['date'] else ''
        desc_escaped = html.escape(a['description'])
        link = f'{SITE_URL}/{a["slug"]}/'
        items.append(
            f'    <item>\n'
            f'      <title>{html.escape(a["title"])}</title>\n'
            f'      <link>{link}</link>\n'
            f'      <description>{desc_escaped}</description>\n'
            f'      <pubDate>{pub_date}</pubDate>\n'
            f'      <author>bernard@zonted.com (Bernard Huang)</author>\n'
            f'      <guid isPermaLink="true">{link}</guid>\n'
            f'    </item>'
        )

    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        '  <channel>\n'
        '    <title>Zonted</title>\n'
        f'    <link>{SITE_URL}/</link>\n'
        '    <description>I test AI tools so you don\'t have to. Honest reviews, real data, and opinions from someone who actually builds with this stuff.</description>\n'
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
    "posts/build-for-agents-price-per-call": ["posts/future-of-software-is-headless", "posts/the-economics-of-the-internet-are-broken", "posts/the-great-api-shutdown"],
    "posts/future-of-content-agentic-data-enrichment": ["posts/training-data-is-the-moat", "posts/aeo-answer-engine-optimization", "posts/the-future-is-synthetic"],
    "posts/future-of-software-is-headless": ["posts/build-for-agents-price-per-call", "posts/the-great-api-shutdown", "posts/the-economics-of-the-internet-are-broken"],
    "posts/google-zero-patience-ai-slop": ["posts/scaling-ai-is-lazy", "posts/what-is-ai-drift-how-to-fix", "posts/aeo-answer-engine-optimization"],
    "posts/kapiko-postmortem": ["posts/ai-music-generation-comparison", "posts/true-cost-of-ai-content-production", "posts/slop-iterate-curate-ai-content"],
    "posts/tabiji-18m-views": ["posts/how-my-agent-made-a-viral-video", "posts/true-cost-of-ai-content-production", "posts/kapiko-postmortem"],
    "posts/how-my-agent-made-a-viral-video": ["posts/tabiji-18m-views", "posts/true-cost-of-ai-content-production", "posts/kapiko-postmortem"],
    "posts/may-2026-recap": ["posts/plan-3x-build-once", "posts/tabiji-18m-views", "posts/how-my-agent-made-a-viral-video"],
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
    "posts/stop-optimizing-ai-infrastructure": ["posts/openclaw-skill-tree", "posts/human-in-the-loop", "posts/build-for-agents-price-per-call"],
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
        '            <section class="zn-recommended">\n'
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
# Main
# ---------------------------------------------------------------------------

def main():
    articles = scan_articles()
    print(f"Found {len(articles)} articles")

    n = generate_homepage(articles)
    print(f"Generated index.html ({n} entries)")

    n = generate_posts_hub(articles)
    print(f"Generated posts/index.html ({n} entries)")

    n = generate_sitemap(articles)
    print(f"Generated sitemap.xml ({n} URLs)")

    n = generate_feed(articles)
    print(f"Generated feed.xml ({n} items)")

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


if __name__ == '__main__':
    main()
