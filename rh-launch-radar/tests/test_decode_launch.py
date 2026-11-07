from __future__ import annotations

import unittest

from rh_radar.decode import decode_pons_launch_log, launch_id


class DecodeLaunchTests(unittest.TestCase):
    def test_decode_pons_final_event_from_live_receipt(self):
        # Fixture from tx 0x70a10650… on 2026-08-09 (ORE launch).
        log = {
            "address": "0xa5aab3f0c6eeadf30ef1d3eb997108e976351feb",
            "topics": [
                "0xdb51ea9ad51ab453a65a4cb7e60c3cb378c9501bb002609f8f97778fb6c4235a",
                "0x000000000000000000000000956a15a411591b9183e2c7e9721ec1a55cc407bb",
                "0x000000000000000000000000af4004a10f09282d1cbc762a91d23613ed732249",
                "0x0000000000000000000000001f7d7550b1b028f7571e69a784071f0205fd2efa",
            ],
            "data": (
                "0x"
                "0000000000000000000000000bd7d308f8e1639fab988df18a8011f41eacad73"
                "0000000000000000000000009b411039d91581bfaa5ab9bac2f72eac690d913e"
                "0000000000000000000000000000000000000000000000000000000000000000"
                "0000000000000000000000000000000000000000000000000000000000000000"
                "000000000000000000000000000000000000000000000000000000000009bed9"
                "0000000000000000000000000000000000000000000000000000000001886edd"
                "00000000000000000000000000000000000000000000000000f084ca934b4000"
            ),
            "blockNumber": "0x1e943d4",
            "transactionHash": "0x70a1065035170a1b3cec5c68218999fa8d9faf9db5eb0a6c1a78a358e56c3446",
            "logIndex": "0xe",
        }
        row = decode_pons_launch_log(log, factory_name="pons_active", mechanism_era="pons-v1")
        self.assertEqual(row["token"], "0x956a15a411591b9183e2c7e9721ec1a55cc407bb")
        self.assertEqual(row["creator"], "0xaf4004a10f09282d1cbc762a91d23613ed732249")
        self.assertEqual(row["pool"], "0x9b411039d91581bfaa5ab9bac2f72eac690d913e")
        self.assertEqual(row["quote"], "0x0bd7d308f8e1639fab988df18a8011f41eacad73")
        self.assertEqual(row["msg_value_wei"], 67700000000000000)
        self.assertEqual(row["launch_id"], launch_id(row["token"], row["pool"]))


if __name__ == "__main__":
    unittest.main()
