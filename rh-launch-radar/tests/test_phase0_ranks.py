from rh_radar.phase0 import ranks_for


def test_first_time_ranks_ahead_of_serial_creators():
    rows = [
        {
            "launch_id": "serial",
            "creator_prior_launches": 12,
            "flow_quote_volume_wei": 10**21,
            "flow_unique_traders": 500,
            "msg_value_wei": 10**18,
            "score": 99.0,
            "creator_prior_win_rate": 0.5,
        },
        {
            "launch_id": "first",
            "creator_prior_launches": 0,
            "flow_quote_volume_wei": 10**18,
            "flow_unique_traders": 10,
            "msg_value_wei": 10**16,
            "score": 1.0,
            "creator_prior_win_rate": None,
        },
    ]
    ranks = ranks_for(rows)
    assert ranks["C1_first_time_then_volume"][0] == "first"
    assert ranks["C2_low_prior_count"][0] == "first"
    assert ranks["B1_volume"][0] == "serial"
