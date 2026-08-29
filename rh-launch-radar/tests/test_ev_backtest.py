from rh_radar.ev_backtest import fold_key, rebuild_survivor


def test_fold_key_hour_and_day():
    # 2026-08-08 15:00:00 UTC
    ts = 1786201200
    assert fold_key(ts, "day") == "2026-08-08"
    assert fold_key(ts, "hour").startswith("2026-08-08T")


def test_decision_v7_passes_when_entry_tvl_clears_floor():
    veto = {"vetoed": True, "reasons": ["V7_liq_floor:96<1000.0", "V6_sell_recovery:0.4<0.5"]}
    ok, reasons = rebuild_survivor({}, veto, decision_tvl_usd=1500.0, floor_usd=1000.0)
    assert ok
    assert reasons == []


def test_decision_v7_keeps_clone_burst():
    veto = {"vetoed": True, "reasons": ["V5_clone_burst", "V7_liq_floor:96<1000.0"]}
    ok, reasons = rebuild_survivor({}, veto, decision_tvl_usd=1500.0, floor_usd=1000.0)
    assert not ok
    assert reasons == ["V5_clone_burst"]
