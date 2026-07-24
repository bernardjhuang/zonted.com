#!/usr/bin/env python3
"""Build the compact /trading YouTube sentiment payload from an analysis run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "trading" / "youtube-sentiment.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Directory containing the YouTube sentiment analysis JSON files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    summary = read_json(args.source / "analysis_summary.json")
    tickers = read_json(args.source / "ticker_sentiment.json")
    creators = read_json(args.source / "creator_sentiment.json")
    videos = read_json(args.source / "video_manifest.json")

    if len(videos) != 125 or len(creators) != 25:
        raise SystemExit(f"Expected 125 videos and 25 creators; got {len(videos)} and {len(creators)}")

    top_25 = tickers[:25]
    mood_counts = {
        mood: sum(row["sentiment"] == mood for row in top_25)
        for mood in ("bullish", "mixed/neutral", "bearish")
    }
    payload = {
        "schema_version": 1,
        "as_of": "2026-07-24T09:21:52-05:00",
        "headline": "Cautious, not euphoric",
        "takeaway": (
            f"Among the 25 most-mentioned assets, {mood_counts['bearish']} have bearish "
            f"cross-creator consensus, {mood_counts['bullish']} bullish, and "
            f"{mood_counts['mixed/neutral']} mixed or neutral."
        ),
        "summary": {
            "channels": 25,
            **summary,
            "videos_without_transcripts": len(videos) - summary["videos_with_transcripts"],
        },
        "freshness_notes": [
            "Six inaccessible transcripts were members-only: three Graham Stephan and three Andrei Jikh videos.",
            "Nate O'Brien's five uploads span 2023–2024 and The Swedish Investor's span 2024–2025; the other 23 channels have at least one 2026 upload.",
        ],
        "methodology": [
            "yt-dlp selected the five latest non-upcoming long-form uploads from each channel's /videos feed and downloaded available English captions.",
            "Ticker detection combined cashtags, parenthesized or all-caps SEC symbols, and a curated company, ETF, index, crypto, and commodity alias map.",
            "Commercial or sponsor-like contexts were separated from headline mention and sentiment totals.",
            "ProsusAI/finbert scored local ticker-bearing transcript chunks. Sentiment is context tone, not a buy or sell recommendation or return forecast.",
            "Ticker consensus gives each creator a ticker-level score, shrinks sparse samples toward neutral, and requires a two-creator edge plus 30% breadth for a bullish or bearish label.",
        ],
        "tickers": tickers,
        "creators": creators,
        "videos": [
            {
                "channel": row["channel"],
                "video_id": row["video_id"],
                "title": row["title"],
                "url": row["url"],
                "upload_date": row.get("upload_date"),
                "duration_seconds": row.get("duration"),
                "transcript_available": bool(row.get("transcript")),
            }
            for row in videos
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"[youtube] wrote {args.output}: {len(tickers)} tickers/assets, "
        f"{len(creators)} creators, {len(videos)} videos"
    )


if __name__ == "__main__":
    main()
