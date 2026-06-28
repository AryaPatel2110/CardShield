from __future__ import annotations

import unittest
from datetime import UTC, datetime

from schemas import (
    FEATURE_COLUMNS,
    SchemaValidationError,
    ScoredTransaction,
    TransactionEvent,
)


def valid_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "trans_num": "transaction-1",
        "amt": 125.5,
        "lat": 41.88,
        "long": -87.63,
        "city_pop": 2_700_000,
        "unix_time": 1_700_000_000,
        "merch_lat": 41.90,
        "merch_long": -87.65,
        "merchant_label": 10,
        "category_label": 4,
        "gender_label": 0,
        "job_label": 100,
        "category": "grocery_pos",
        "is_fraud": 0,
    }


class TransactionEventTests(unittest.TestCase):
    def test_valid_event_has_features_in_training_order(self) -> None:
        event = TransactionEvent.from_mapping(valid_payload())

        self.assertEqual(tuple(event.feature_values()), FEATURE_COLUMNS)
        self.assertEqual(event.trans_num, "transaction-1")

    def test_invalid_coordinates_are_rejected(self) -> None:
        payload = valid_payload()
        payload["lat"] = 100

        with self.assertRaises(SchemaValidationError):
            TransactionEvent.from_mapping(payload)

    def test_unknown_schema_version_is_rejected(self) -> None:
        payload = valid_payload()
        payload["schema_version"] = 2

        with self.assertRaises(SchemaValidationError):
            TransactionEvent.from_mapping(payload)

    def test_scored_transaction_serializes_model_metadata(self) -> None:
        scored = ScoredTransaction(
            transaction=TransactionEvent.from_mapping(valid_payload()),
            prediction=1,
            fraud_probability=0.91,
            model_version="test-v1",
            scored_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        result = scored.to_dict()

        self.assertEqual(result["is_fraud_prediction"], 1)
        self.assertEqual(result["model_version"], "test-v1")


if __name__ == "__main__":
    unittest.main()
