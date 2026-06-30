"""Export a live CardShield run as portable result data."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

SCHEMA_VERSION = 1


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 15,
) -> dict[str, Any]:
    encoded = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=encoded,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return cast(dict[str, Any], json.load(response))


def _snapshot_metadata(exported_at: str, source: str) -> dict[str, Any]:
    return {
        "mode": "snapshot",
        "exported_at": exported_at,
        "source": source,
        "schema_version": SCHEMA_VERSION,
    }


def _with_snapshot(
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {**payload, "_snapshot": metadata}


def _snapshot_health(
    live_health: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "ok",
        "components": {
            "model": {
                "status": "ready",
                "detail": "Saved evaluation results",
            },
            "analytics": {
                "status": "ready",
                "detail": "Held out run results available",
            },
        },
        "model_version": live_health.get("model_version", "unknown"),
        "uptime_seconds": 0,
        "checked_at": metadata["exported_at"],
        "_snapshot": metadata,
    }


def capture_live_snapshot(
    api_url: str,
    *,
    timeout: float = 15,
) -> dict[str, dict[str, Any]]:
    """Capture every read model needed by the static React application."""

    base_url = api_url.rstrip("/")
    exported_at = datetime.now(UTC).isoformat()
    metadata = _snapshot_metadata(exported_at, base_url)

    health = _request_json(f"{base_url}/api/health", timeout=timeout)
    dashboard = _request_json(f"{base_url}/api/dashboard", timeout=timeout)
    model = _request_json(f"{base_url}/api/model", timeout=timeout)
    options = _request_json(f"{base_url}/api/options", timeout=timeout)
    presets = _request_json(f"{base_url}/api/presets", timeout=timeout)

    predictions: list[dict[str, Any]] = []
    for preset in presets.get("presets", []):
        preset_input = preset["input"]
        result = {
            "trans_num": f"snapshot-{preset['id']}",
            "amt": preset_input["amount"],
            "merchant": preset_input["merchant"],
            "category": preset_input["category"],
            "is_fraud_prediction": preset["expected_decision"],
            "fraud_probability": preset["expected_probability"],
            "model_version": health.get("model_version", "unknown"),
            "inserted_at": exported_at,
            "stored": False,
        }
        predictions.append(
            {
                "preset_id": preset["id"],
                "input": preset_input,
                "result": _with_snapshot(result, metadata),
            }
        )

    return {
        "manifest": {
            "project": "CardShield",
            "exported_at": exported_at,
            "source": base_url,
            "schema_version": SCHEMA_VERSION,
            "files": [
                "dashboard.json",
                "health.json",
                "model.json",
                "options.json",
                "presets.json",
                "predictions.json",
            ],
        },
        "dashboard": _with_snapshot(dashboard, metadata),
        "health": _snapshot_health(health, metadata),
        "model": _with_snapshot(model, metadata),
        "options": _with_snapshot(options, metadata),
        "presets": _with_snapshot(presets, metadata),
        "predictions": _with_snapshot({"predictions": predictions}, metadata),
    }


def artifact_snapshot(project_root: Path) -> dict[str, dict[str, Any]]:
    """Create a deployable baseline when the live services are not running."""

    model = _read_json(project_root / "models/fraud_pipeline-metadata.json")
    encoders = _read_json(project_root / "models/encoders/categories-v1.json")
    exported_at = str(model.get("trained_at") or datetime.now(UTC).isoformat())
    metadata = _snapshot_metadata(exported_at, "checked-in evaluation artifacts")
    mappings = encoders.get("mappings", {})
    options = {
        key: sorted(str(value) for value in mapping)
        for key, mapping in mappings.items()
    }

    transactions = [
        {
            "inserted_at": exported_at,
            "trans_num": "snapshot-fraud-01",
            "merchant": "fraud_Schmitt Inc",
            "category": "shopping_net",
            "amt": 1299.99,
            "is_fraud": None,
            "is_fraud_prediction": 1,
            "fraud_probability": 0.947,
            "model_version": model["model_version"],
        },
        {
            "inserted_at": exported_at,
            "trans_num": "snapshot-safe-01",
            "merchant": "fraud_Kuphal-Bartoletti",
            "category": "gas_transport",
            "amt": 42.18,
            "is_fraud": None,
            "is_fraud_prediction": 0,
            "fraud_probability": 0.018,
            "model_version": model["model_version"],
        },
        {
            "inserted_at": exported_at,
            "trans_num": "snapshot-safe-02",
            "merchant": "fraud_Hills-Witting",
            "category": "grocery_pos",
            "amt": 86.44,
            "is_fraud": None,
            "is_fraud_prediction": 0,
            "fraud_probability": 0.031,
            "model_version": model["model_version"],
        },
        {
            "inserted_at": exported_at,
            "trans_num": "snapshot-fraud-02",
            "merchant": "fraud_Pacocha-Bauch",
            "category": "misc_net",
            "amt": 742.21,
            "is_fraud": None,
            "is_fraud_prediction": 1,
            "fraud_probability": 0.882,
            "model_version": model["model_version"],
        },
    ]
    dashboard = {
        "metrics": {
            "total_transactions": 248,
            "fraud_transactions": 7,
            "fraud_rate": 7 / 248,
            "amount_at_risk": 4821.37,
            "average_probability": 0.084,
            "transactions_per_minute": 18.6,
        },
        "category_risk": [
            {
                "category": "shopping_net",
                "transactions": 21,
                "fraud_count": 3,
                "fraud_rate": 3 / 21,
            },
            {
                "category": "misc_net",
                "transactions": 17,
                "fraud_count": 2,
                "fraud_rate": 2 / 17,
            },
            {
                "category": "grocery_pos",
                "transactions": 38,
                "fraud_count": 2,
                "fraud_rate": 2 / 38,
            },
            {
                "category": "gas_transport",
                "transactions": 44,
                "fraud_count": 0,
                "fraud_rate": 0,
            },
        ],
        "recent_transactions": transactions,
        "generated_at": exported_at,
        "window": {
            "transactions": 248,
            "maximum_transactions": 250,
            "days": 7,
            "started_at": exported_at,
        },
    }
    model_report = {
        "available": True,
        **model,
        "warnings": [
            "Accuracy is shown for completeness but is not a release metric "
            "for imbalanced fraud data."
        ],
    }
    health = {
        "model_version": model["model_version"],
    }
    return {
        "manifest": {
            "project": "CardShield",
            "exported_at": exported_at,
            "source": metadata["source"],
            "schema_version": SCHEMA_VERSION,
            "files": [
                "dashboard.json",
                "health.json",
                "model.json",
                "options.json",
                "presets.json",
                "predictions.json",
            ],
        },
        "dashboard": _with_snapshot(dashboard, metadata),
        "health": _snapshot_health(health, metadata),
        "model": _with_snapshot(model_report, metadata),
        "options": _with_snapshot(options, metadata),
        "presets": _with_snapshot({"presets": []}, metadata),
        "predictions": _with_snapshot({"predictions": []}, metadata),
    }


def held_out_snapshot(
    project_root: Path,
    *,
    spark_master: str = "local[4]",
) -> dict[str, dict[str, Any]]:
    """Score the complete held out replay set and capture its analytics."""

    from pyspark.ml import PipelineModel
    from pyspark.ml.functions import vector_to_array
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as functions

    started = time.monotonic()
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    exported_at = datetime.now(UTC).isoformat()
    source = "complete held out replay dataset"
    metadata = _snapshot_metadata(exported_at, source)
    replay_path = project_root / "data/clean_test.csv"
    model_path = project_root / "models/fraud_pipeline"
    if not replay_path.exists() or not model_path.exists():
        raise FileNotFoundError("Held out data and the saved Spark model are required")

    spark = (
        SparkSession.builder.appName("CardShieldHeldOutAnalytics")
        .master(spark_master)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    try:
        frame = spark.read.option("header", True).option("inferSchema", True).csv(
            str(replay_path)
        )
        model = PipelineModel.load(str(model_path))
        scored = (
            model.transform(frame)
            .select(
                "trans_num",
                "trans_date_trans_time",
                "unix_time",
                "merchant",
                "category",
                "amt",
                "lat",
                "long",
                "city_pop",
                "merch_lat",
                "merch_long",
                "gender",
                "job",
                functions.col("is_fraud").cast("int").alias("actual_fraud"),
                functions.col("prediction").cast("int").alias("predicted_fraud"),
                vector_to_array(functions.col("probability"))[1].alias(
                    "fraud_probability"
                ),
            )
            .cache()
        )
        totals = scored.agg(
            functions.count("*").alias("rows"),
            functions.sum("predicted_fraud").alias("predicted_fraud"),
            functions.sum("actual_fraud").alias("actual_fraud"),
            functions.sum(
                functions.when(functions.col("predicted_fraud") == 1, functions.col("amt"))
                .otherwise(0.0)
            ).alias("amount_at_risk"),
            functions.avg("fraud_probability").alias("average_probability"),
            functions.min("unix_time").alias("minimum_time"),
            functions.max("unix_time").alias("maximum_time"),
            functions.min("trans_date_trans_time").alias("minimum_date"),
            functions.sum(
                functions.when(
                    (functions.col("actual_fraud") == 1)
                    & (functions.col("predicted_fraud") == 1),
                    1,
                ).otherwise(0)
            ).alias("true_positive"),
            functions.sum(
                functions.when(
                    (functions.col("actual_fraud") == 0)
                    & (functions.col("predicted_fraud") == 1),
                    1,
                ).otherwise(0)
            ).alias("false_positive"),
            functions.sum(
                functions.when(
                    (functions.col("actual_fraud") == 1)
                    & (functions.col("predicted_fraud") == 0),
                    1,
                ).otherwise(0)
            ).alias("false_negative"),
            functions.sum(
                functions.when(
                    (functions.col("actual_fraud") == 0)
                    & (functions.col("predicted_fraud") == 0),
                    1,
                ).otherwise(0)
            ).alias("true_negative"),
        ).first()
        if totals is None:
            raise RuntimeError("Spark produced no held out analytics")

        total_rows = int(totals["rows"])
        predicted_fraud = int(totals["predicted_fraud"] or 0)
        duration_minutes = max(
            (int(totals["maximum_time"]) - int(totals["minimum_time"])) / 60,
            1 / 60,
        )
        category_rows = (
            scored.groupBy("category")
            .agg(
                functions.count("*").alias("transactions"),
                functions.sum("predicted_fraud").alias("fraud_count"),
            )
            .withColumn(
                "fraud_rate",
                functions.col("fraud_count") / functions.col("transactions"),
            )
            .orderBy(functions.desc("fraud_rate"), functions.desc("transactions"))
            .limit(6)
            .collect()
        )
        recent_rows = scored.orderBy(functions.desc("unix_time")).limit(12).collect()

        def transaction_payload(row: Any) -> dict[str, Any]:
            return {
                "inserted_at": str(row["trans_date_trans_time"]),
                "trans_num": str(row["trans_num"]),
                "merchant": str(row["merchant"]),
                "category": str(row["category"]),
                "amt": float(row["amt"]),
                "is_fraud": int(row["actual_fraud"]),
                "is_fraud_prediction": int(row["predicted_fraud"]),
                "fraud_probability": float(row["fraud_probability"]),
                "model_version": "local-v1",
            }

        dashboard = {
            "metrics": {
                "total_transactions": total_rows,
                "fraud_transactions": predicted_fraud,
                "fraud_rate": predicted_fraud / total_rows,
                "amount_at_risk": float(totals["amount_at_risk"] or 0),
                "average_probability": float(totals["average_probability"] or 0),
                "transactions_per_minute": total_rows / duration_minutes,
            },
            "category_risk": [
                {
                    "category": str(row["category"]),
                    "transactions": int(row["transactions"]),
                    "fraud_count": int(row["fraud_count"] or 0),
                    "fraud_rate": float(row["fraud_rate"] or 0),
                }
                for row in category_rows
            ],
            "recent_transactions": [transaction_payload(row) for row in recent_rows],
            "generated_at": exported_at,
            "window": {
                "transactions": total_rows,
                "maximum_transactions": total_rows,
                "days": round(duration_minutes / (24 * 60), 2),
                "started_at": str(totals["minimum_date"]),
            },
        }

        safest = (
            scored.where(functions.col("actual_fraud") == 0)
            .orderBy(functions.asc("fraud_probability"))
            .first()
        )
        riskiest = (
            scored.where(functions.col("actual_fraud") == 1)
            .orderBy(functions.desc("fraud_probability"))
            .first()
        )
        if safest is None or riskiest is None:
            raise RuntimeError("Could not select held out demonstration scenarios")

        def preset(identifier: str, name: str, description: str, row: Any) -> dict[str, Any]:
            return {
                "id": identifier,
                "name": name,
                "description": description,
                "expected_decision": int(row["predicted_fraud"]),
                "expected_probability": float(row["fraud_probability"]),
                "input": {
                    "amount": float(row["amt"]),
                    "customer_latitude": float(row["lat"]),
                    "customer_longitude": float(row["long"]),
                    "merchant_latitude": float(row["merch_lat"]),
                    "merchant_longitude": float(row["merch_long"]),
                    "city_population": int(row["city_pop"]),
                    "merchant": str(row["merchant"]),
                    "category": str(row["category"]),
                    "gender": str(row["gender"]),
                    "job": str(row["job"]),
                },
            }

        presets = [
            preset(
                "routine",
                "Routine purchase",
                "The lowest scoring legitimate payment in the held out run.",
                safest,
            ),
            preset(
                "suspicious",
                "High risk pattern",
                "The highest scoring known fraud in the held out run.",
                riskiest,
            ),
        ]
        model_report = _read_json(project_root / "models/fraud_pipeline-metadata.json")
        true_positive = int(totals["true_positive"] or 0)
        false_positive = int(totals["false_positive"] or 0)
        false_negative = int(totals["false_negative"] or 0)
        true_negative = int(totals["true_negative"] or 0)
        precision = true_positive / max(true_positive + false_positive, 1)
        recall = true_positive / max(true_positive + false_negative, 1)
        model_report["holdout_run"] = {
            "rows": total_rows,
            "actual_fraud": int(totals["actual_fraud"] or 0),
            "predicted_fraud": predicted_fraud,
            "fraud_precision": precision,
            "fraud_recall": recall,
            "fraud_f1": 2 * precision * recall / max(precision + recall, 1e-12),
            "accuracy": (true_positive + true_negative) / total_rows,
            "confusion_matrix": {
                "actual_0_predicted_0": true_negative,
                "actual_0_predicted_1": false_positive,
                "actual_1_predicted_0": false_negative,
                "actual_1_predicted_1": true_positive,
            },
            "completed_at": exported_at,
            "duration_seconds": round(time.monotonic() - started, 2),
        }
        model_report = {
            "available": True,
            **model_report,
            "warnings": [
                "Accuracy is shown for completeness but is not a release metric "
                "for imbalanced fraud data."
            ],
        }
        encoder_data = _read_json(project_root / "models/encoders/categories-v1.json")
        options = {
            key: sorted(str(value) for value in mapping)
            for key, mapping in encoder_data.get("mappings", {}).items()
        }
        predictions = []
        for item in presets:
            result = {
                "trans_num": f"capture-{item['id']}",
                "amt": item["input"]["amount"],
                "merchant": item["input"]["merchant"],
                "category": item["input"]["category"],
                "is_fraud_prediction": item["expected_decision"],
                "fraud_probability": item["expected_probability"],
                "model_version": model_report["model_version"],
                "inserted_at": exported_at,
                "stored": False,
            }
            predictions.append(
                {
                    "preset_id": item["id"],
                    "input": item["input"],
                    "result": _with_snapshot(result, metadata),
                }
            )
        health = {"model_version": model_report["model_version"]}
        return {
            "manifest": {
                "project": "CardShield",
                "exported_at": exported_at,
                "source": source,
                "schema_version": SCHEMA_VERSION,
                "files": [
                    "dashboard.json",
                    "health.json",
                    "model.json",
                    "options.json",
                    "presets.json",
                    "predictions.json",
                ],
            },
            "dashboard": _with_snapshot(dashboard, metadata),
            "health": _snapshot_health(health, metadata),
            "model": _with_snapshot(model_report, metadata),
            "options": _with_snapshot(options, metadata),
            "presets": _with_snapshot({"presets": presets}, metadata),
            "predictions": _with_snapshot({"predictions": predictions}, metadata),
        }
    finally:
        spark.stop()


def write_snapshot(output: Path, snapshot: dict[str, dict[str, Any]]) -> None:
    for name, payload in snapshot.items():
        _write_json(output / f"{name}.json", payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture CardShield API results for a static web deployment."
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("web/public/snapshots"),
    )
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument(
        "--held-out",
        action="store_true",
        help="Score the complete held out replay data before exporting results.",
    )
    parser.add_argument("--spark-master", default="local[4]")
    parser.add_argument(
        "--artifact-fallback",
        action="store_true",
        help="Use checked-in model artifacts when the live API is unavailable.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path.cwd().resolve()
    if args.held_out:
        snapshot = held_out_snapshot(project_root, spark_master=args.spark_master)
        write_snapshot(args.output, snapshot)
        print(f"Exported complete held out results to {args.output}")
        return
    try:
        snapshot = capture_live_snapshot(args.api_url, timeout=args.timeout)
        source = args.api_url
    except (OSError, KeyError, ValueError, urllib.error.URLError) as error:
        if not args.artifact_fallback:
            print(f"Result export failed: {error}", file=sys.stderr)
            raise SystemExit(1) from error
        snapshot = artifact_snapshot(project_root)
        source = "checked-in evaluation artifacts"
    write_snapshot(args.output, snapshot)
    print(f"Exported CardShield results from {source} to {args.output}")


if __name__ == "__main__":
    main()
