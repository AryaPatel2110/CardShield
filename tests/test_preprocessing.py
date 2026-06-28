from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from config import Settings
from preprocessing import CategoryEncoders, preprocess


class CategoryEncoderTests(unittest.TestCase):
    def test_encoder_is_stable_and_handles_unseen_values(self) -> None:
        training = pd.DataFrame(
            {
                "merchant": ["b", "a"],
                "category": ["food", "travel"],
                "gender": ["F", "M"],
                "job": ["engineer", "teacher"],
            }
        )
        validation = pd.DataFrame(
            {
                "merchant": ["a", "never-seen"],
                "category": ["food", "food"],
                "gender": ["F", "F"],
                "job": ["engineer", "engineer"],
            }
        )

        encoders = CategoryEncoders.fit(training)
        transformed = encoders.transform(validation)

        self.assertEqual(transformed.loc[0, "merchant_label"], 0)
        self.assertEqual(transformed.loc[1, "merchant_label"], -1)

    def test_encoder_round_trip(self) -> None:
        training = pd.DataFrame(
            {
                "merchant": ["a"],
                "category": ["food"],
                "gender": ["F"],
                "job": ["engineer"],
            }
        )
        encoders = CategoryEncoders.fit(training)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "encoders.json"
            encoders.save(path)
            loaded = CategoryEncoders.load(path)

        self.assertEqual(loaded, encoders)

    def test_preprocess_preserves_validation_and_unknown_category(self) -> None:
        columns = {
            "trans_date_trans_time": ["2020-01-01"] * 4,
            "cc_num": [1, 2, 3, 4],
            "merchant": ["a", "b", "a", "b"],
            "category": ["food", "travel", "food", "travel"],
            "amt": [10.0, 20.0, 30.0, 40.0],
            "first": ["A"] * 4,
            "last": ["B"] * 4,
            "gender": ["F", "M", "F", "M"],
            "street": ["street"] * 4,
            "city": ["city"] * 4,
            "state": ["IL"] * 4,
            "zip": [60601] * 4,
            "lat": [41.0] * 4,
            "long": [-87.0] * 4,
            "city_pop": [1000] * 4,
            "job": ["engineer", "teacher", "engineer", "teacher"],
            "dob": ["1990-01-01"] * 4,
            "trans_num": ["t1", "t2", "t3", "t4"],
            "unix_time": [1, 2, 3, 4],
            "merch_lat": [41.1] * 4,
            "merch_long": [-87.1] * 4,
            "is_fraud": [0, 1, 0, 1],
        }
        train = pd.DataFrame(columns)
        validation = train.iloc[:2].copy()
        validation["merchant"] = ["unseen", "a"]

        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw_train = root / "raw-train.csv"
            raw_validation = root / "raw-validation.csv"
            train.to_csv(raw_train)
            validation.to_csv(raw_validation)

            settings = replace(
                Settings(project_root=root),
                raw_train_path=raw_train,
                raw_test_path=raw_validation,
                processed_train_path=root / "train.csv",
                processed_validation_path=root / "validation.csv",
                replay_path=root / "replay.csv",
                encoder_path=root / "encoders.json",
            )
            result = preprocess(settings)
            transformed_validation = pd.read_csv(settings.processed_validation_path)

        self.assertEqual(result["train_rows"], 4)
        self.assertEqual(result["validation_rows"], 2)
        self.assertEqual(transformed_validation.loc[0, "merchant_label"], -1)


if __name__ == "__main__":
    unittest.main()
