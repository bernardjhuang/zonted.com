from rh_radar.honest_labels import attach_short_horizon_exits


def test_attach_short_horizon_exits_from_checkpoints():
    row = {
        "entry_ok": True,
        "rug_checkpoints": [
            {
                "horizon_sec": 3600,
                "sell_recovery_vs_entry": 3.5,
                "rug_reasons": [],
            },
            {
                "horizon_sec": 21600,
                "sell_recovery_vs_entry": 0.2,
                "rug_reasons": ["sell_recovery:0.2<0.5"],
            },
        ],
    }
    attach_short_horizon_exits(row)
    assert row["gross_multiple_1h"] == 3.5
    assert row["executable_winner_250_1h"] is True
    assert row["rug_1h"] is False
    assert row["gross_multiple_6h"] == 0.2
    assert row["rug_6h"] is True
    assert row["executable_winner_250_6h"] is False
