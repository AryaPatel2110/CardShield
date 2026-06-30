"""Synchronous model inference and categorical encoding for the HTTP API."""

from __future__ import annotations

import logging
import os
import pickle
import sys
import threading
from pathlib import Path
from typing import Any

from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession

from config import Settings
from preprocessing import CATEGORICAL_COLUMNS, CategoryEncoders
from schemas import ScoredTransaction, TransactionEvent

LOGGER = logging.getLogger(__name__)


class EncoderService:
    """Load the current JSON encoder or the legacy trusted sklearn artifact."""

    def __init__(self, settings: Settings) -> None:
        if settings.encoder_path.exists():
            self._encoders = CategoryEncoders.load(settings.encoder_path)
        elif settings.legacy_encoder_path.exists():
            self._encoders = self._load_legacy(settings.legacy_encoder_path)
        else:
            raise FileNotFoundError(
                "No categorical encoder found. Run cardshield-preprocess or set "
                "CARDSHIELD_ENCODER_PATH."
            )

    @staticmethod
    def _load_legacy(path: Path) -> CategoryEncoders:
        # This project-owned artifact is retained only for compatibility with the
        # checked-in model. New deployments should use the JSON encoder.
        with path.open("rb") as artifact:
            raw: Any = pickle.load(artifact)  # noqa: S301
        if not isinstance(raw, dict):
            raise ValueError("Legacy encoder artifact must contain a dictionary")

        mappings: dict[str, dict[str, int]] = {}
        for column in CATEGORICAL_COLUMNS:
            encoder = raw.get(column)
            classes = getattr(encoder, "classes_", None)
            if classes is None:
                raise ValueError(f"Legacy encoder is missing {column!r} classes")
            mappings[column] = {
                str(value): index for index, value in enumerate(classes.tolist())
            }
        return CategoryEncoders(mappings=mappings)

    def encode(self, column: str, value: str) -> int:
        mapping = self._encoders.mappings.get(column)
        if mapping is None:
            raise ValueError(f"Unsupported categorical field: {column}")
        return mapping.get(value, self._encoders.unknown_value)

    def options(self) -> dict[str, list[str]]:
        return {
            column: list(mapping)
            for column, mapping in self._encoders.mappings.items()
        }


class ModelScorer:
    """Own one local Spark session and serialize access to its pipeline model."""

    def __init__(self, settings: Settings) -> None:
        if not settings.model_path.exists():
            raise FileNotFoundError(
                f"Spark model not found at {settings.model_path}. Run cardshield-train first."
            )

        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
        self._settings = settings
        self._lock = threading.Lock()
        self._spark = (
            SparkSession.builder.appName("CardShieldAPI")
            .master("local[2]")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.pyspark.python", sys.executable)
            .config("spark.pyspark.driver.python", sys.executable)
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .getOrCreate()
        )
        self._spark.sparkContext.setLogLevel("ERROR")
        self._model = PipelineModel.load(str(settings.model_path))
        LOGGER.info("Fraud model loaded", extra={"model_path": settings.model_path})

    def score(self, transaction: TransactionEvent) -> ScoredTransaction:
        """Score one validated transaction with the production Spark pipeline."""
        with self._lock:
            frame = self._spark.createDataFrame([transaction.feature_values()])
            row = (
                self._model.transform(frame)
                .select("prediction", "probability")
                .first()
            )
        if row is None:
            raise RuntimeError("The fraud model returned no prediction")

        probability_vector = row["probability"]
        fraud_probability = float(probability_vector[1])
        return ScoredTransaction.create(
            transaction,
            prediction=int(row["prediction"]),
            fraud_probability=fraud_probability,
            model_version=self._settings.model_version,
        )

    def score_many(
        self,
        transactions: list[TransactionEvent],
    ) -> list[ScoredTransaction]:
        """Score a small batch efficiently, primarily for deterministic demo presets."""
        if not transactions:
            return []
        rows = [
            {"trans_num": transaction.trans_num, **transaction.feature_values()}
            for transaction in transactions
        ]
        with self._lock:
            predictions = (
                self._model.transform(self._spark.createDataFrame(rows))
                .select("trans_num", "prediction", "probability")
                .collect()
            )
        by_id = {transaction.trans_num: transaction for transaction in transactions}
        return [
            ScoredTransaction.create(
                by_id[str(row["trans_num"])],
                prediction=int(row["prediction"]),
                fraud_probability=float(row["probability"][1]),
                model_version=self._settings.model_version,
            )
            for row in predictions
        ]

    def close(self) -> None:
        self._spark.stop()
