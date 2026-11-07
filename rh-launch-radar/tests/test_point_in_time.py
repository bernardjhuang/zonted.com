from __future__ import annotations

import unittest


def assert_no_lookahead(feature_row: dict, decision_ts: int) -> None:
    """Fail closed: any feature available_at after decision_ts is leakage."""
    available_at = feature_row.get("available_at")
    if available_at is None:
        raise AssertionError("available_at missing — fail closed")
    if available_at > decision_ts:
        raise AssertionError(
            f"lookahead: available_at {available_at} > decision_ts {decision_ts} for {feature_row.get('launch_id')}"
        )
    for key, value in feature_row.items():
        if key.endswith("_available_at") and isinstance(value, (int, float)) and value > decision_ts:
            raise AssertionError(f"lookahead in {key}: {value} > {decision_ts}")


class PointInTimeTests(unittest.TestCase):
    def test_accepts_causal_row(self):
        row = {"launch_id": "x", "available_at": 100, "decision_ts": 100, "flow_swaps": 3}
        assert_no_lookahead(row, 100)

    def test_rejects_future_available_at(self):
        row = {"launch_id": "x", "available_at": 101, "flow_swaps": 3}
        with self.assertRaises(AssertionError):
            assert_no_lookahead(row, 100)

    def test_rejects_missing_available_at(self):
        with self.assertRaises(AssertionError):
            assert_no_lookahead({"launch_id": "x"}, 100)


if __name__ == "__main__":
    unittest.main()
