"""FastAPI bridge for CardShield model inference and dashboard data."""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app_logging import configure_logging
from cassandra_repository import CassandraRepository
from config import Settings
from model_service import EncoderService, ModelScorer
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
    category_risk = [
        {
            "category": category,
            "transactions": count,
            "fraud_count": category_fraud[category],
            "fraud_rate": category_fraud[category] / count,
        }
        for category, count in category_total.most_common(6)
    ]
    return {
        "metrics": {
            "total_transactions": total,
            "fraud_transactions": len(fraud_rows),
            "fraud_rate": len(fraud_rows) / total if total else 0.0,
            "amount_at_risk": amount_at_risk,
            "average_probability": average_probability,
        },
        "category_risk": category_risk,
        "recent_transactions": [_serialize_row(row) for row in rows[:12]],
        "generated_at": datetime.now(UTC).isoformat(),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    current_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.encoders = EncoderService(current_settings)
        app.state.scorer = ModelScorer(current_settings)
        try:
            app.state.repository = CassandraRepository(current_settings)
            app.state.storage_error = None
        except Exception as error:
            LOGGER.exception("Cassandra is unavailable; API started in inference-only mode")
            app.state.repository = None
            app.state.storage_error = str(error)
        yield
        repository = app.state.repository
        if repository is not None:
            repository.close()
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
        return {
            "status": "ok" if request.app.state.repository is not None else "degraded",
            "model": "ready",
            "storage": (
                "connected" if request.app.state.repository is not None else "unavailable"
            ),
            "model_version": current_settings.model_version,
        }

    @app.get("/api/options")
    def options(request: Request) -> dict[str, list[str]]:
        encoders: EncoderService = request.app.state.encoders
        return encoders.options()

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
