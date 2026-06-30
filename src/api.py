"""FastAPI bridge for CardShield model inference and dashboard data."""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app_logging import configure_logging
from cassandra_repository import CassandraRepository
from config import Settings
from model_service import EncoderService, ModelScorer
from producer import TransactionProducer
from schemas import SchemaValidationError, TransactionEvent

LOGGER = logging.getLogger(__name__)


class PredictionRequest(BaseModel):
    amount: float = Field(gt=0, le=1_000_000)
    customer_latitude: float = Field(ge=-90, le=90)
    customer_longitude: float = Field(ge=-180, le=180)
    merchant_latitude: float = Field(ge=-90, le=90)
    merchant_longitude: float = Field(ge=-180, le=180)
    city_population: int = Field(gt=0)
    merchant: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    gender: str = Field(min_length=1, max_length=20)
    job: str = Field(min_length=1, max_length=200)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


def _pipeline_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    serialized = [_serialize_row(row) for row in rows]
    latest = serialized[-1] if serialized else {}
    started_at = serialized[0]["occurred_at"] if serialized else None
    completed_at = (
        latest.get("occurred_at")
        if latest.get("stage") == "CASSANDRA_PERSISTED"
        else None
    )
    latency_ms = None
    if started_at and completed_at:
        latency_ms = round(
            (
                datetime.fromisoformat(completed_at)
                - datetime.fromisoformat(started_at)
            ).total_seconds()
            * 1000
        )
    return {
        "transaction_id": latest.get("trans_num"),
        "status": "complete" if completed_at else "processing",
        "stages": serialized,
        "latency_ms": latency_ms,
        "prediction": (
            {
                "trans_num": latest["trans_num"],
                "amt": latest["amt"],
                "merchant": latest["merchant"],
                "category": latest["category"],
                "is_fraud_prediction": latest["is_fraud_prediction"],
                "fraud_probability": latest["fraud_probability"],
                "model_version": latest["model_version"],
                "inserted_at": latest["occurred_at"],
                "stored": True,
            }
            if completed_at
            else None
        ),
    }


def _preset_input(transaction: TransactionEvent) -> dict[str, Any]:
    return {
        "amount": transaction.amt,
        "customer_latitude": transaction.lat,
        "customer_longitude": transaction.long,
        "merchant_latitude": transaction.merch_lat,
        "merchant_longitude": transaction.merch_long,
        "city_population": transaction.city_pop,
        "merchant": transaction.merchant,
        "category": transaction.category,
        "gender": transaction.gender,
        "job": transaction.job,
    }


def _load_demo_presets(settings: Settings, scorer: ModelScorer) -> list[dict[str, Any]]:
    if not settings.replay_path.exists():
        return []
    legitimate = pd.DataFrame()
    suspicious = pd.DataFrame()
    required = {"is_fraud", "trans_num", "amt"}
    for chunk in pd.read_csv(settings.replay_path, low_memory=False, chunksize=50_000):
        if not required.issubset(chunk.columns):
            return []
        legitimate = pd.concat(
            [legitimate, chunk[chunk["is_fraud"] == 0]],
            ignore_index=True,
        ).nsmallest(32, "amt")
        suspicious = pd.concat(
            [suspicious, chunk[chunk["is_fraud"] == 1]],
            ignore_index=True,
        ).nlargest(64, "amt")
    historical_candidates = [
        TransactionEvent.from_mapping(row)
        for row in pd.concat([legitimate, suspicious]).to_dict(orient="records")
    ]
    now = datetime.now(UTC)
    candidates = [
        replace(
            transaction,
            unix_time=int(now.timestamp()),
            trans_date_trans_time=now.isoformat(),
        )
        for transaction in historical_candidates
    ]
    scored = scorer.score_many(candidates)
    safe_rows = [item for item in scored if item.transaction.is_fraud == 0]
    fraud_rows = [item for item in scored if item.transaction.is_fraud == 1]
    if not safe_rows or not fraud_rows:
        return []
    safest = min(safe_rows, key=lambda item: item.fraud_probability)
    riskiest = max(fraud_rows, key=lambda item: item.fraud_probability)
    return [
        {
            "id": "routine",
            "name": "Routine purchase",
            "description": "A low-risk legitimate sample from the held-out replay period.",
            "expected_decision": safest.prediction,
            "expected_probability": safest.fraud_probability,
            "input": _preset_input(safest.transaction),
        },
        {
            "id": "suspicious",
            "name": "High-risk pattern",
            "description": "The highest-scoring known fraud among sampled held-out events.",
            "expected_decision": riskiest.prediction,
            "expected_probability": riskiest.fraud_probability,
            "input": _preset_input(riskiest.transaction),
        },
    ]


def _build_event(payload: PredictionRequest, encoders: EncoderService) -> TransactionEvent:
    now = datetime.now(UTC)
    return TransactionEvent.from_mapping(
        {
            "trans_num": uuid.uuid4().hex,
            "amt": payload.amount,
            "lat": payload.customer_latitude,
            "long": payload.customer_longitude,
            "city_pop": payload.city_population,
            "unix_time": int(now.timestamp()),
            "merch_lat": payload.merchant_latitude,
            "merch_long": payload.merchant_longitude,
            "merchant_label": encoders.encode("merchant", payload.merchant),
            "category_label": encoders.encode("category", payload.category),
            "gender_label": encoders.encode("gender", payload.gender),
            "job_label": encoders.encode("job", payload.job),
            "merchant": payload.merchant,
            "category": payload.category,
            "gender": payload.gender,
            "job": payload.job,
            "trans_date_trans_time": now.isoformat(),
        }
    )


def _dashboard_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    fraud_rows = [row for row in rows if int(row["is_fraud_prediction"] or 0) == 1]
    amount_at_risk = sum(float(row["amt"] or 0) for row in fraud_rows)
    average_probability = (
        sum(float(row["fraud_probability"] or 0) for row in rows) / total
        if total
        else 0.0
    )
    category_total = Counter(str(row["category"] or "Unknown") for row in rows)
    category_fraud = Counter(str(row["category"] or "Unknown") for row in fraud_rows)
    category_risk = sorted(
        [
        {
            "category": category,
            "transactions": count,
            "fraud_count": category_fraud[category],
            "fraud_rate": category_fraud[category] / count,
        }
            for category, count in category_total.items()
        ],
        key=lambda item: (item["fraud_rate"], item["transactions"]),
        reverse=True,
    )[:6]
    window_minutes = 0.0
    if len(rows) > 1:
        newest = rows[0]["inserted_at"]
        oldest = rows[-1]["inserted_at"]
        window_minutes = max((newest - oldest).total_seconds() / 60, 1 / 60)
    return {
        "metrics": {
            "total_transactions": total,
            "fraud_transactions": len(fraud_rows),
            "fraud_rate": len(fraud_rows) / total if total else 0.0,
            "amount_at_risk": amount_at_risk,
            "average_probability": average_probability,
            "transactions_per_minute": total / window_minutes if window_minutes else 0.0,
        },
        "category_risk": category_risk,
        "recent_transactions": [_serialize_row(row) for row in rows[:12]],
        "generated_at": datetime.now(UTC).isoformat(),
        "window": {
            "transactions": total,
            "maximum_transactions": 250,
            "days": 7,
            "started_at": (
                rows[-1]["inserted_at"].isoformat() if rows else None
            ),
        },
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    current_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.started_at = datetime.now(UTC)
        app.state.encoders = EncoderService(current_settings)
        app.state.scorer = ModelScorer(current_settings)
        try:
            app.state.repository = CassandraRepository(current_settings)
            app.state.storage_error = None
        except Exception as error:
            LOGGER.exception("Cassandra is unavailable; API started in inference-only mode")
            app.state.repository = None
            app.state.storage_error = str(error)
        try:
            app.state.producer = TransactionProducer(current_settings)
            app.state.kafka_error = None
        except Exception as error:
            LOGGER.exception("Kafka is unavailable; live pipeline mode is disabled")
            app.state.producer = None
            app.state.kafka_error = str(error)
        app.state.demo_presets = None
        yield
        repository = app.state.repository
        if repository is not None:
            repository.close()
        producer = app.state.producer
        if producer is not None:
            producer.close()
        app.state.scorer.close()

    app = FastAPI(
        title="CardShield API",
        version="1.0.0",
        description="Fraud inference and operational dashboard endpoints.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(current_settings.web_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        storage_ready = request.app.state.repository is not None
        kafka_ready = request.app.state.producer is not None
        return {
            "status": "ok" if storage_ready and kafka_ready else "degraded",
            "components": {
                "api": {"status": "ready", "detail": "FastAPI accepting requests"},
                "model": {"status": "ready", "detail": "Spark ML model loaded"},
                "kafka": {
                    "status": "ready" if kafka_ready else "unavailable",
                    "detail": current_settings.kafka_input_topic,
                },
                "cassandra": {
                    "status": "ready" if storage_ready else "unavailable",
                    "detail": current_settings.cassandra_keyspace,
                },
            },
            "model_version": current_settings.model_version,
            "uptime_seconds": round(
                (datetime.now(UTC) - request.app.state.started_at).total_seconds()
            ),
            "checked_at": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/options")
    def options(request: Request) -> dict[str, list[str]]:
        encoders: EncoderService = request.app.state.encoders
        return encoders.options()

    @app.get("/api/presets")
    def presets(request: Request) -> dict[str, Any]:
        cached: list[dict[str, Any]] | None = request.app.state.demo_presets
        if cached is None:
            cached = _load_demo_presets(current_settings, request.app.state.scorer)
            request.app.state.demo_presets = cached
        return {"presets": cached}

    @app.get("/api/model")
    def model_report() -> dict[str, Any]:
        if not current_settings.model_metadata_path.exists():
            return {
                "available": False,
                "model_version": current_settings.model_version,
                "message": "Evaluation metadata is not available. Train the release model first.",
            }
        metadata: dict[str, Any] = json.loads(
            current_settings.model_metadata_path.read_text(encoding="utf-8")
        )
        metrics = metadata.get("metrics", {})
        warnings: list[str] = []
        if metrics.get("fraud_recall", 0) < 0.5:
            warnings.append("Fraud recall is below the 50% demo readiness gate.")
        if metrics.get("fraud_precision", 0) < 0.2:
            warnings.append("Fraud precision is below the 20% demo readiness gate.")
        warnings.append(
            "Accuracy is shown for completeness but is not a release metric "
            "for imbalanced fraud data."
        )
        return {"available": True, **metadata, "warnings": warnings}

    @app.get("/api/dashboard")
    def dashboard(request: Request, limit: int = 250) -> dict[str, Any]:
        repository: CassandraRepository | None = request.app.state.repository
        if repository is None:
            raise HTTPException(
                status_code=503,
                detail=f"Cassandra is unavailable: {request.app.state.storage_error}",
            )
        safe_limit = min(max(limit, 1), 1000)
        return _dashboard_payload(repository.recent_transactions(limit=safe_limit))

    @app.post("/api/predict")
    def predict(payload: PredictionRequest, request: Request) -> dict[str, Any]:
        encoders: EncoderService = request.app.state.encoders
        scorer: ModelScorer = request.app.state.scorer
        repository: CassandraRepository | None = request.app.state.repository
        try:
            event = _build_event(payload, encoders)
            scored = scorer.score(event)
        except (SchemaValidationError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        stored = False
        if repository is not None:
            try:
                repository.write_scored(scored)
                stored = True
            except Exception:
                LOGGER.exception("Prediction succeeded but Cassandra persistence failed")

        result = scored.to_dict()
        result["stored"] = stored
        return result

    @app.post("/api/pipeline")
    def submit_pipeline(payload: PredictionRequest, request: Request) -> dict[str, Any]:
        encoders: EncoderService = request.app.state.encoders
        producer: TransactionProducer | None = request.app.state.producer
        repository: CassandraRepository | None = request.app.state.repository
        if producer is None:
            raise HTTPException(
                status_code=503,
                detail=f"Kafka is unavailable: {request.app.state.kafka_error}",
            )
        if repository is None:
            raise HTTPException(
                status_code=503,
                detail="Live pipeline tracing requires Cassandra",
            )
        event = _build_event(payload, encoders)
        accepted_at = datetime.now(UTC)
        repository.record_pipeline_stage(
            event.trans_num,
            "API_ACCEPTED",
            occurred_at=accepted_at,
            detail="Transaction validated against schema version 1",
            amount=event.amt,
            merchant=event.merchant,
            category=event.category,
        )
        try:
            metadata = producer.send(event).get(timeout=10)
        except Exception as error:
            LOGGER.exception("Unable to publish interactive transaction")
            raise HTTPException(status_code=503, detail="Kafka publish failed") from error
        repository.record_pipeline_stage(
            event.trans_num,
            "KAFKA_PUBLISHED",
            detail=f"Published to partition {metadata.partition} at offset {metadata.offset}",
            amount=event.amt,
            merchant=event.merchant,
            category=event.category,
        )
        return {
            "transaction_id": event.trans_num,
            "status": "processing",
            "poll_url": f"/api/pipeline/{event.trans_num}",
        }

    @app.get("/api/pipeline/{transaction_id}")
    def pipeline_status(transaction_id: str, request: Request) -> dict[str, Any]:
        repository: CassandraRepository | None = request.app.state.repository
        if repository is None:
            raise HTTPException(status_code=503, detail="Cassandra is unavailable")
        rows = repository.pipeline_trace(transaction_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Pipeline trace not found")
        return _pipeline_payload(rows)

    return app


app = create_app()


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
