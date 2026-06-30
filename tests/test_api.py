from __future__ import annotations

import unittest
from datetime import UTC, datetime
from decimal import Decimal

from api import PredictionRequest, _dashboard_payload, _pipeline_payload


class ApiTests(unittest.TestCase):
    def test_dashboard_payload_aggregates_recent_predictions(self) -> None:
        rows = [
            {
                "inserted_at": datetime.now(UTC),
                "trans_num": "fraud-1",
                "merchant": "Store A",
                "category": "shopping_net",
                "amt": Decimal("125.50"),
                "is_fraud": None,
                "is_fraud_prediction": 1,
                "fraud_probability": 0.91,
                "model_version": "test",
            },
            {
                "inserted_at": datetime.now(UTC),
                "trans_num": "safe-1",
                "merchant": "Store B",
                "category": "gas_transport",
                "amt": Decimal("40.00"),
                "is_fraud": None,
                "is_fraud_prediction": 0,
                "fraud_probability": 0.02,
                "model_version": "test",
            },
        ]

        result = _dashboard_payload(rows)

        self.assertEqual(result["metrics"]["total_transactions"], 2)
        self.assertEqual(result["metrics"]["fraud_transactions"], 1)
        self.assertEqual(result["metrics"]["amount_at_risk"], 125.5)
        self.assertEqual(result["recent_transactions"][0]["amt"], 125.5)

    def test_pipeline_payload_reports_completion_and_latency(self) -> None:
        rows = [
            {
                "trans_num": "trace-1",
                "occurred_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                "stage": "API_ACCEPTED",
                "detail": "validated",
                "amt": Decimal("25.00"),
                "merchant": "Store",
                "category": "food",
                "fraud_probability": None,
                "is_fraud_prediction": None,
                "model_version": None,
            },
            {
                "trans_num": "trace-1",
                "occurred_at": datetime(2026, 1, 1, 12, 0, 2, tzinfo=UTC),
                "stage": "CASSANDRA_PERSISTED",
                "detail": "stored",
                "amt": Decimal("25.00"),
                "merchant": "Store",
                "category": "food",
                "fraud_probability": 0.04,
                "is_fraud_prediction": 0,
                "model_version": "test-v1",
            },
        ]

        result = _pipeline_payload(rows)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["latency_ms"], 2000)
        self.assertTrue(result["prediction"]["stored"])

    def test_prediction_request_rejects_invalid_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            PredictionRequest(
                amount=25,
                customer_latitude=100,
                customer_longitude=-74,
                merchant_latitude=40,
                merchant_longitude=-73,
                city_population=1000,
                merchant="Merchant",
                category="gas_transport",
                gender="F",
                job="Engineer",
            )


if __name__ == "__main__":
    unittest.main()
