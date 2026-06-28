from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import ConfigurationError, Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_resolve_paths_from_project_root(self) -> None:
        with TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {"CARDSHIELD_PROJECT_ROOT": directory},
                clear=True,
            ):
                settings = Settings.from_env()

        root = Path(directory).resolve()
        self.assertEqual(settings.project_root, root)
        self.assertEqual(settings.model_path, root / "models/fraud_pipeline")
        self.assertEqual(settings.kafka_input_topic, "transactions.v1")

    def test_cassandra_credentials_must_be_set_together(self) -> None:
        with patch.dict(
            os.environ,
            {"CARDSHIELD_CASSANDRA_USERNAME": "cardshield"},
            clear=True,
        ):
            with self.assertRaises(ConfigurationError):
                Settings.from_env()


if __name__ == "__main__":
    unittest.main()
