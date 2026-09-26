from rh_radar.paper_ledger import select_trades, summarize


def _row(launch_id: str, creator: str, score: float, g: float, ts: int) -> dict:
    return {
        "launch_id": launch_id,
        "creator": creator,
        "score": score,
        "gross_multiple_1h": g,
        "rug_1h": g < 0.5,
        "executable_winner_250_1h": g >= 3.0,
        "first_liq_ts": ts,
        "first_liq_block": ts,
        "token": "0x",
        "pool": "0x",
        "entry_tvl_usd": 2000,
        "flow_quote_volume_wei": 1,
        "creator_prior_launches": 0,
    }


def test_select_trades_top_k_and_creator_dedupe():
    # Same UTC hour
    ts = 1786201200
    rows = [
        _row("a", "0xc1", 10, 4.0, ts),
        _row("b", "0xc1", 9, 0.2, ts + 1),  # same creator — skipped when dedupe
        _row("c", "0xc2", 8, 1.1, ts + 2),
        _row("d", "0xc3", 7, 0.3, ts + 3),
        _row("e", "0xc4", 6, 0.4, ts + 4),
    ]
    trades = select_trades(rows, k=3, fold_grain="hour", dedupe_creator=True)
    assert [t["launch_id"] for t in trades] == ["a", "c", "d"]
    assert trades[0]["pnl_per_dollar"] == 3.0


def test_creator_cooldown_across_hours():
    ts = 1786201200  # hour H
    rows = [
        _row("a", "0xc1", 10, 4.0, ts),
        _row("b", "0xc2", 9, 1.0, ts + 60),
        _row("c", "0xc1", 10, 0.2, ts + 3600),  # next hour, same creator — cooldown
        _row("d", "0xc3", 8, 1.2, ts + 3601),
    ]
    trades = select_trades(
        rows, k=2, fold_grain="hour", dedupe_creator=True, creator_cooldown_sec=7200
    )
    assert [t["launch_id"] for t in trades] == ["a", "b", "d"]


def test_first_time_creator_only():
    ts = 1786201200
    rows = [
        {**_row("a", "0xc1", 10, 4.0, ts), "creator_prior_launches": 0},
        {**_row("b", "0xc2", 9, 2.0, ts + 1), "creator_prior_launches": 3},
        {**_row("c", "0xc3", 8, 1.5, ts + 2), "creator_prior_launches": 0},
    ]
    trades = select_trades(
        rows, k=3, fold_grain="hour", dedupe_creator=False, first_time_creator_only=True
    )
    assert [t["launch_id"] for t in trades] == ["a", "c"]


def test_summarize_fold_means():
    trades = [
        {"fold": "h1", "gross_multiple_1h": 3.0, "rug_1h": False, "executable_winner_250_1h": True, "launch_id": "a"},
        {"fold": "h1", "gross_multiple_1h": 1.0, "rug_1h": False, "executable_winner_250_1h": False, "launch_id": "b"},
        {"fold": "h2", "gross_multiple_1h": 0.2, "rug_1h": True, "executable_winner_250_1h": False, "launch_id": "c"},
    ]
    s = summarize(trades, n_candidates=10)
    assert s["n_trades"] == 3
    assert s["mean_of_fold_means"] == (2.0 + 0.2) / 2
    assert s["winner_launch_ids"] == ["a"]
