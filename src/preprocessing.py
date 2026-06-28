"""Reproducible preprocessing for Sparkov fraud transactions."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app_logging import configure_logging
from config import Settings
from schemas import FEATURE_COLUMNS

LOGGER = logging.getLogger(__name__)

CATEGORICAL_COLUMNS: tuple[str, ...] = ("merchant", "category", "gender", "job")
MODEL_COLUMNS: tuple[str, ...] = (*FEATURE_COLUMNS, "is_fraud")
RAW_NUMERIC_FEATURES: tuple[str, ...] = FEATURE_COLUMNS[:7]


@dataclass(frozen=True, slots=True)
class CategoryEncoders:
    """Stable categorical mappings with an explicit unknown value."""

    mappings: dict[str, dict[str, int]]
    unknown_value: int = -1
    version: int = 1

    @classmethod
    def fit(cls, frame: pd.DataFrame) -> CategoryEncoders:
        mappings: dict[str, dict[str, int]] = {}
        for column in CATEGORICAL_COLUMNS:
            if column not in frame:
                raise ValueError(f"Training data is missing categorical column {column}")
            values = sorted(str(value) for value in frame[column].dropna().unique())
            mappings[column] = {value: index for index, value in enumerate(values)}
        return cls(mappings=mappings)

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        for column, mapping in self.mappings.items():
            if column not in result:
                raise ValueError(f"Data is missing categorical column {column}")
            result[f"{column}_label"] = (
                result[column].astype(str).map(mapping).fillna(self.unknown_value).astype("int32")
            )
        return result

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "unknown_value": self.unknown_value,
            "mappings": self.mappings,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> CategoryEncoders:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            mappings={
                column: {str(key): int(value) for key, value in mapping.items()}
                for column, mapping in payload["mappings"].items()
            },
            unknown_value=int(payload["unknown_value"]),
            version=int(payload["version"]),
        )


def read_raw_transactions(path: Path, *, sample_size: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    frame = pd.read_csv(path, low_memory=False, index_col=0)
    if sample_size is not None and sample_size < len(frame):
        fraud = frame[frame["is_fraud"] == 1]
        legitimate = frame[frame["is_fraud"] == 0]
        observed_fraud_rate = len(fraud) / len(frame)
        fraud_count = min(
            max(round(sample_size * observed_fraud_rate), 1),
            len(fraud),
            sample_size - 1,
        )
        legitimate_count = min(sample_size - fraud_count, len(legitimate))
        sampled_fraud = fraud.sample(n=fraud_count, random_state=42)
        sampled_legitimate = legitimate.sample(
            n=legitimate_count,
            random_state=42,
        )
        frame = (
            pd.concat([sampled_fraud, sampled_legitimate], ignore_index=True)
            .sample(frac=1, random_state=42)
            .reset_index(drop=True)
        )
    return frame


def validate_columns(frame: pd.DataFrame, *, source: str) -> None:
    required = {
        "trans_num",
        "is_fraud",
        *RAW_NUMERIC_FEATURES,
        *CATEGORICAL_COLUMNS,
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def preprocess(
    settings: Settings,
    *,
    sample_size: int | None = None,
) -> dict[str, int]:
    """Create leakage-safe train, validation, and replay datasets."""
    LOGGER.info("Reading raw training data", extra={"path": settings.raw_train_path})
    raw_train = read_raw_transactions(settings.raw_train_path, sample_size=sample_size)
    LOGGER.info("Reading raw validation data", extra={"path": settings.raw_test_path})
    raw_validation = read_raw_transactions(settings.raw_test_path, sample_size=sample_size)

    validate_columns(raw_train, source="training data")
    validate_columns(raw_validation, source="validation data")

    encoders = CategoryEncoders.fit(raw_train)
    encoded_train = encoders.transform(raw_train)
    encoded_validation = encoders.transform(raw_validation)

    for output in (
        settings.processed_train_path,
        settings.processed_validation_path,
        settings.replay_path,
    ):
        output.parent.mkdir(parents=True, exist_ok=True)

    encoded_train.loc[:, MODEL_COLUMNS].to_csv(
        settings.processed_train_path,
        index=False,
    )
    encoded_validation.loc[:, MODEL_COLUMNS].to_csv(
        settings.processed_validation_path,
        index=False,
    )
    encoded_validation.to_csv(settings.replay_path, index=False)
    encoders.save(settings.encoder_path)

    result = {
        "train_rows": len(encoded_train),
        "validation_rows": len(encoded_validation),
        "train_fraud_rows": int(encoded_train["is_fraud"].sum()),
        "validation_fraud_rows": int(encoded_validation["is_fraud"].sum()),
    }
    LOGGER.info(
        "Preprocessing complete",
        extra={
            **result,
            "encoder_path": settings.encoder_path,
            "train_output": settings.processed_train_path,
            "validation_output": settings.processed_validation_path,
        },
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional maximum rows per source file for a local smoke test.",
    )
    parser.add_argument("--env-file", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    preprocess(settings, sample_size=args.sample_size)


if __name__ == "__main__":
    main()
