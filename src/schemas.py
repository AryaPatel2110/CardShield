"""Versioned transaction contracts shared across CardShield services."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = 1

FEATURE_COLUMNS: tuple[str, ...] = (
    "amt",
    "lat",
    "long",
    "city_pop",
    "unix_time",
    "merch_lat",
    "merch_long",
    "merchant_label",
    "category_label",
    "gender_label",
    "job_label",
)


class SchemaValidationError(ValueError):
    """Raised when an event cannot satisfy the transaction contract."""


def _required(data: Mapping[str, Any], name: str) -> Any:
    value = data.get(name)
    if value is None or value == "":
        raise SchemaValidationError(f"Missing required field: {name}")
    return value


def _as_float(data: Mapping[str, Any], name: str) -> float:
    try:
        value = float(_required(data, name))
    except (TypeError, ValueError) as error:
        raise SchemaValidationError(f"{name} must be numeric") from error
    if not math.isfinite(value):
        raise SchemaValidationError(f"{name} must be finite")
    return value


def _as_int(data: Mapping[str, Any], name: str) -> int:
    try:
        return int(_required(data, name))
    except (TypeError, ValueError) as error:
        raise SchemaValidationError(f"{name} must be an integer") from error


@dataclass(frozen=True, slots=True)
class TransactionEvent:
    """Validated transaction received from Kafka.

    The field names intentionally remain compatible with the Sparkov dataset
    while the envelope adds a stable schema version.
    """

    trans_num: str
    amt: float
    lat: float
    long: float
    city_pop: int
    unix_time: int
    merch_lat: float
    merch_long: float
    merchant_label: int
    category_label: int
    gender_label: int
    job_label: int

    merchant: str | None = None
    category: str | None = None
    gender: str | None = None
    job: str | None = None
    trans_date_trans_time: str | None = None
    cc_num: int | None = None
    is_fraud: int | None = None
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> TransactionEvent:
        """Validate and normalize an untrusted event mapping."""
        raw_version = data.get("schema_version", SCHEMA_VERSION)
        version = SCHEMA_VERSION if raw_version is None else int(raw_version)
        if version != SCHEMA_VERSION:
            raise SchemaValidationError(
                f"Unsupported schema_version {version}; expected {SCHEMA_VERSION}"
            )

        amount = _as_float(data, "amt")
        latitude = _as_float(data, "lat")
        longitude = _as_float(data, "long")
        merchant_latitude = _as_float(data, "merch_lat")
        merchant_longitude = _as_float(data, "merch_long")

        if amount < 0:
            raise SchemaValidationError("amt cannot be negative")
        if not -90 <= latitude <= 90 or not -90 <= merchant_latitude <= 90:
            raise SchemaValidationError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180 or not -180 <= merchant_longitude <= 180:
            raise SchemaValidationError("longitude must be between -180 and 180")

        actual_fraud = data.get("is_fraud")
        if actual_fraud is not None:
            actual_fraud = int(actual_fraud)
            if actual_fraud not in (0, 1):
                raise SchemaValidationError("is_fraud must be 0 or 1")

        cc_num = data.get("cc_num")

        return cls(
            trans_num=str(_required(data, "trans_num")),
            amt=amount,
            lat=latitude,
            long=longitude,
            city_pop=_as_int(data, "city_pop"),
            unix_time=_as_int(data, "unix_time"),
            merch_lat=merchant_latitude,
            merch_long=merchant_longitude,
            merchant_label=_as_int(data, "merchant_label"),
            category_label=_as_int(data, "category_label"),
            gender_label=_as_int(data, "gender_label"),
            job_label=_as_int(data, "job_label"),
            merchant=str(data["merchant"]) if data.get("merchant") is not None else None,
            category=str(data["category"]) if data.get("category") is not None else None,
            gender=str(data["gender"]) if data.get("gender") is not None else None,
            job=str(data["job"]) if data.get("job") is not None else None,
            trans_date_trans_time=(
                str(data["trans_date_trans_time"])
                if data.get("trans_date_trans_time") is not None
                else None
            ),
            cc_num=int(cc_num) if cc_num is not None else None,
            is_fraud=actual_fraud,
            schema_version=version,
        )

    def feature_values(self) -> dict[str, float | int]:
        """Return model features in the exact training order."""
        return {name: getattr(self, name) for name in FEATURE_COLUMNS}

    def to_dict(self, *, exclude_none: bool = True) -> dict[str, Any]:
        """Serialize the event to a JSON-compatible dictionary."""
        result = asdict(self)
        if exclude_none:
            return {key: value for key, value in result.items() if value is not None}
        return result


@dataclass(frozen=True, slots=True)
class ScoredTransaction:
    """A transaction enriched with model inference metadata."""

    transaction: TransactionEvent
    prediction: int
    fraud_probability: float
    model_version: str
    scored_at: datetime

    def __post_init__(self) -> None:
        if self.prediction not in (0, 1):
            raise SchemaValidationError("prediction must be 0 or 1")
        if not 0 <= self.fraud_probability <= 1:
            raise SchemaValidationError("fraud_probability must be between 0 and 1")
        if self.scored_at.tzinfo is None:
            raise SchemaValidationError("scored_at must include a timezone")

    @classmethod
    def create(
        cls,
        transaction: TransactionEvent,
        *,
        prediction: int,
        fraud_probability: float,
        model_version: str,
    ) -> ScoredTransaction:
        return cls(
            transaction=transaction,
            prediction=prediction,
            fraud_probability=fraud_probability,
            model_version=model_version,
            scored_at=datetime.now(UTC),
        )

    def to_dict(self) -> dict[str, Any]:
        result = self.transaction.to_dict()
        result.update(
            {
                "is_fraud_prediction": self.prediction,
                "fraud_probability": self.fraud_probability,
                "model_version": self.model_version,
                "inserted_at": self.scored_at.isoformat(),
            }
        )
        return result
