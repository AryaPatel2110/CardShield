from __future__ import annotations

import unittest

from static_export import _snapshot_health, _snapshot_metadata, _with_snapshot


class StaticExportTests(unittest.TestCase):
    def test_snapshot_metadata_is_added_without_mutating_payload(self) -> None:
        payload = {"metrics": {"total_transactions": 12}}
        metadata = _snapshot_metadata("2026-06-30T12:00:00+00:00", "test")

        result = _with_snapshot(payload, metadata)

        self.assertNotIn("_snapshot", payload)
        self.assertEqual(result["_snapshot"]["mode"], "snapshot")
        self.assertEqual(result["metrics"]["total_transactions"], 12)

    def test_snapshot_health_reports_saved_analytics_as_ready(self) -> None:
        metadata = _snapshot_metadata("2026-06-30T12:00:00+00:00", "test")

        result = _snapshot_health({"model_version": "test-v1"}, metadata)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["components"]["analytics"]["status"], "ready")
        self.assertEqual(result["model_version"], "test-v1")


if __name__ == "__main__":
    unittest.main()
