from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from producer import iter_replay_events


class ReplayReaderTests(unittest.TestCase):
    def test_reader_ignores_csv_index_and_invalid_rows(self) -> None:
        valid = {
            "trans_num": "valid",
            "amt": 25.0,
            "lat": 41.0,
            "long": -87.0,
            "city_pop": 1000,
            "unix_time": 1,
            "merch_lat": 42.0,
            "merch_long": -88.0,
            "merchant_label": 1,
            "category_label": 2,
            "gender_label": 0,
            "job_label": 3,
            "schema_version": 1,
        }
        invalid = {**valid, "trans_num": "invalid", "amt": -1}

        with TemporaryDirectory() as directory:
            path = Path(directory) / "replay.csv"
            pd.DataFrame([valid, invalid]).to_csv(path)
            events = list(iter_replay_events(path))

        self.assertEqual([event.trans_num for event in events], ["valid"])


if __name__ == "__main__":
    unittest.main()
