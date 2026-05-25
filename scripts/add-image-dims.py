#!/usr/bin/env python3
"""Add width/height attributes to every <img> tag in posts/*/index.html.

Browsers can pre-allocate layout space when width+height are present,
eliminating CLS (Cumulative Layout Shift) on every page load. The
attribute values are intrinsic pixel dimensions — CSS still controls
display size, but the aspect ratio is locked.

For local images, dimensions are read from the PNG/JPEG headers on
disk (no PIL dependency). For R2 images (img.zonted.com/...), a HEAD
request fetches the first chunk and we parse the header bytes.

Cached results live in scripts/.image-dims-cache.json so re-runs are
fast and offline-safe.

Usage:
  python3 scripts/add-image-dims.py
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "scripts" / ".image-dims-cache.json"


def png_dims(data: bytes) -> tuple[int, int] | None:
    # PNG signature is 8 bytes, IHDR is next 25 bytes (incl. 4-byte length prefix + "IHDR" + 13 bytes data + CRC)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR width/height are 4-byte BE ints starting at offset 16
    if len(data) < 24:
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpeg_dims(data: bytes) -> tuple[int, int] | None:
    # Walk JPEG segments looking for SOFn marker
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            # SOFn: length(2), precision(1), height(2), width(2)
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        if marker == 0xD8 or marker == 0xD9 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        # Segment length
        seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + seg_len
    return None


def gif_dims(data: bytes) -> tuple[int, int] | None:
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    if len(data) < 10:
        return None
    w, h = struct.unpack("<HH", data[6:10])
    return w, h


def webp_dims(data: bytes) -> tuple[int, int] | None:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    # VP8 / VP8L / VP8X variants. Simplest VP8X first.
    if data[12:16] == b"VP8X":
        # 4-byte length, 4-byte flags, then 6 bytes for canvas size (3 each, BE-1)
        w = struct.unpack("<I", data[24:27] + b"\x00")[0] + 1
        h = struct.unpack("<I", data[27:30] + b"\x00")[0] + 1
        return w, h
    if data[12:16] == b"VP8L":
        # Skip 4-byte length, then signature byte (0x2f), then 14 bits W and 14 bits H
        b1, b2, b3, b4 = data[21], data[22], data[23], data[24]
        w = ((b2 & 0x3F) << 8 | b1) + 1
        h = ((b4 & 0x0F) << 10 | b3 << 2 | (b2 >> 6)) + 1
        return w, h
    if data[12:16] == b"VP8 ":
        # Skip 4-byte length, 3-byte tag, then 2-byte 0x9d012a, then W and H (LE)
        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return w, h
    return None


def avif_dims(data: bytes) -> tuple[int, int] | None:
    # ISOBMFF box structure. Look for "ispe" box (Image Spatial Extents).
    idx = data.find(b"ispe")
    if idx == -1 or idx + 20 > len(data):
        return None
    # 8-byte box header (size + type), 4-byte version+flags, 4-byte width, 4-byte height
    w, h = struct.unpack(">II", data[idx + 8 : idx + 16])
    return w, h


def read_dims(data: bytes) -> tuple[int, int] | None:
    for fn in (png_dims, jpeg_dims, gif_dims, webp_dims, avif_dims):
        d = fn(data)
        if d:
            return d
    return None


def resolve_local(src: str, post_dir: Path) -> Path | None:
    """Map an <img src> to a filesystem path inside the repo, if local."""
    if src.startswith(("http://", "https://", "//", "data:")):
        return None
    if src.startswith("/"):
        return ROOT / src.lstrip("/")
    # Relative — resolve against the post dir
    return (post_dir / src).resolve()


def fetch_remote(src: str) -> bytes | None:
    """Fetch first 64KB from an http(s) URL. Returns None on error."""
    try:
        req = urllib.request.Request(src, headers={"Range": "bytes=0-65535", "User-Agent": "zonted-img-dims/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read(65536)
    except Exception as e:
        print(f"  fetch failed: {src[:80]} → {e}", file=sys.stderr)
        return None


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))


def main() -> int:
    cache: dict[str, list[int]] = load_cache()
    cache_hits = 0
    cache_misses = 0

    # img tags WITHOUT width AND height — leave already-annotated ones alone.
    # Match <img ... src="..."> where neither width= nor height= appears in the tag.
    img_re = re.compile(r'<img\b(?![^>]*\bwidth=)(?![^>]*\bheight=)([^>]*?)\bsrc=(["\'])([^"\']+)\2([^>]*?)>', re.IGNORECASE)

    edited_files = 0
    edited_tags = 0
    skipped_tags = 0

    posts_dir = ROOT / "posts"
    for post_dir in sorted(posts_dir.iterdir()):
        idx = post_dir / "index.html"
        if not idx.is_file():
            continue
        s = idx.read_text()

        def patch(m: re.Match) -> str:
            nonlocal cache_hits, cache_misses, edited_tags, skipped_tags
            pre, _q, src, post = m.group(1), m.group(2), m.group(3), m.group(4)

            if src in cache:
                w, h = cache[src]
                cache_hits += 1
            else:
                if src.startswith(("http://", "https://", "//")):
                    url = src if not src.startswith("//") else "https:" + src
                    data = fetch_remote(url)
                else:
                    p = resolve_local(src, post_dir)
                    if not p or not p.exists():
                        skipped_tags += 1
                        return m.group(0)
                    with open(p, "rb") as f:
                        data = f.read(65536)
                if not data:
                    skipped_tags += 1
                    return m.group(0)
                dims = read_dims(data)
                if not dims:
                    skipped_tags += 1
                    return m.group(0)
                w, h = dims
                cache[src] = [w, h]
                cache_misses += 1

            edited_tags += 1
            return f'<img{pre} src="{src}" width="{w}" height="{h}"{post}>'

        new_s, n = img_re.subn(patch, s)
        if n and new_s != s:
            idx.write_text(new_s)
            edited_files += 1

    save_cache(cache)
    print(f"Edited {edited_tags} img tags across {edited_files} posts.")
    print(f"Cache hits: {cache_hits}  misses (newly resolved): {cache_misses}")
    print(f"Skipped (unreadable/unknown format): {skipped_tags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
