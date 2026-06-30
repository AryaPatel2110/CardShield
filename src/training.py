"""Train and evaluate the CardShield Spark ML fraud classifier."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator
from pyspark.ml.feature import OneHotEncoder, SQLTransformer, StringIndexer, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as functions

from app_logging import configure_logging
from config import Settings
from schemas import FEATURE_COLUMNS

LOGGER = logging.getLogger(__name__)

NUMERIC_MODEL_FEATURES: tuple[str, ...] = (
    "amt",
    "lat",
    "long",
    "city_pop",
    "merch_lat",
    "merch_long",
    "distance_km",
    "transaction_hour",
    "transaction_day_of_week",
)
CATEGORICAL_LABELS: tuple[str, ...] = (
    "merchant_label",
    "category_label",
    "gender_label",
    "job_label",
)


def create_spark_session() -> SparkSession:
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    return (
        SparkSession.builder.appName("CardShieldTraining")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .getOrCreate()
    )


def load_dataset(spark: SparkSession, path: Path) -> DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {path}")
    frame = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    missing = sorted({*FEATURE_COLUMNS, "is_fraud"}.difference(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
    return frame.select(*FEATURE_COLUMNS, "is_fraud").dropna()


def add_class_weights(frame: DataFrame) -> tuple[DataFrame, float]:
    counts = {
        int(row["is_fraud"]): int(row["count"])
        for row in frame.groupBy("is_fraud").count().collect()
    }
    fraud_count = counts.get(1, 0)
    legitimate_count = counts.get(0, 0)
    if fraud_count == 0 or legitimate_count == 0:
        raise ValueError("Training data must contain both legitimate and fraudulent rows")
    fraud_weight = legitimate_count / fraud_count
    weighted = frame.withColumn(
        "class_weight",
        functions.when(functions.col("is_fraud") == 1, functions.lit(fraud_weight)).otherwise(
            functions.lit(1.0)
        ),
    )
    return weighted, fraud_weight


def evaluate(predictions: DataFrame) -> dict[str, Any]:
    binary = BinaryClassificationEvaluator(
        labelCol="is_fraud",
        rawPredictionCol="rawPrediction",
    )
    multiclass = MulticlassClassificationEvaluator(
        labelCol="is_fraud",
        predictionCol="prediction",
    )
    positive_class = MulticlassClassificationEvaluator(
        labelCol="is_fraud",
        predictionCol="prediction",
        metricLabel=1.0,
    )

    confusion = {
        f"actual_{int(row['is_fraud'])}_predicted_{int(row['prediction'])}": int(row["count"])
        for row in predictions.groupBy("is_fraud", "prediction").count().collect()
    }

    return {
        "area_under_pr": binary.setMetricName("areaUnderPR").evaluate(predictions),
        "area_under_roc": binary.setMetricName("areaUnderROC").evaluate(predictions),
        "fraud_precision": positive_class.setMetricName("precisionByLabel").evaluate(predictions),
        "fraud_recall": positive_class.setMetricName("recallByLabel").evaluate(predictions),
        "fraud_f1": positive_class.setMetricName("fMeasureByLabel").evaluate(predictions),
        "weighted_f1": multiclass.setMetricName("f1").evaluate(predictions),
        "accuracy": multiclass.setMetricName("accuracy").evaluate(predictions),
        "confusion_matrix": confusion,
    }


def threshold_diagnostics(predictions: DataFrame) -> dict[str, Any]:
    """Select an operating point on calibration data under a recall constraint."""
    scored = predictions.withColumn(
        "fraud_probability",
        vector_to_array(functions.col("probability"))[1],
    )
    candidates: list[dict[str, float]] = []
    for threshold in (0.3, 0.4, 0.5, 0.55, 0.6, 0.625, 0.65, 0.675, 0.7, 0.75):
        counts = {
            (int(row["is_fraud"]), int(row["threshold_prediction"])): int(row["count"])
            for row in (
                scored.withColumn(
                    "threshold_prediction",
                    (functions.col("fraud_probability") >= threshold).cast("int"),
                )
                .groupBy("is_fraud", "threshold_prediction")
                .count()
                .collect()
            )
        }
        true_positive = counts.get((1, 1), 0)
        false_positive = counts.get((0, 1), 0)
        false_negative = counts.get((1, 0), 0)
        precision = true_positive / (true_positive + false_positive or 1)
        recall = true_positive / (true_positive + false_negative or 1)
        f1 = 2 * precision * recall / (precision + recall or 1)
        candidates.append(
            {
                "threshold": threshold,
                "fraud_precision": precision,
                "fraud_recall": recall,
                "fraud_f1": f1,
            }
        )
    recall_eligible = [item for item in candidates if item["fraud_recall"] >= 0.6]
    recommended = max(
        recall_eligible or candidates,
        key=lambda item: item["fraud_f1"],
    )
    return {
        "candidates": candidates,
        "selected_on_calibration": recommended,
        "applied_threshold": recommended["threshold"],
        "selection_policy": "maximum fraud F1 among candidates with at least 60% recall",
        "note": (
            "Selected on the earlier half of the held-out period and evaluated on "
            "the later half. Production approval still requires explicit fraud-loss "
            "and false-decline costs."
        ),
    }


def train_model(
    settings: Settings,
    *,
    num_trees: int = 100,
    max_depth: int = 12,
    seed: int = 42,
) -> dict[str, Any]:
    spark = create_spark_session()
    try:
        training = load_dataset(spark, settings.processed_train_path)
        validation = load_dataset(spark, settings.processed_validation_path)
        cutoff = validation.approxQuantile("unix_time", [0.5], 0.001)[0]
        calibration = validation.filter(functions.col("unix_time") <= cutoff)
        evaluation = validation.filter(functions.col("unix_time") > cutoff)
        weighted_training, fraud_weight = add_class_weights(training)

        feature_engineering = SQLTransformer(
            statement="""
                SELECT *,
                    pmod(CAST(FLOOR(unix_time / 3600) AS INT), 24)
                        AS transaction_hour,
                    pmod(CAST(FLOOR(unix_time / 86400) + 4 AS INT), 7)
                        AS transaction_day_of_week,
                    SQRT(
                        POW(lat - merch_lat, 2) +
                        POW((long - merch_long) * COS(RADIANS(lat)), 2)
                    ) * 111.32 AS distance_km
                FROM __THIS__
            """
        )
        indexers = [
            StringIndexer(
                inputCol=column,
                outputCol=f"{column}_index",
                handleInvalid="keep",
            )
            for column in CATEGORICAL_LABELS
        ]
        categorical_vectors = [f"{column}_vector" for column in CATEGORICAL_LABELS]
        one_hot = OneHotEncoder(
            inputCols=[f"{column}_index" for column in CATEGORICAL_LABELS],
            outputCols=categorical_vectors,
            handleInvalid="keep",
            dropLast=False,
        )
        assembler = VectorAssembler(
            inputCols=[*NUMERIC_MODEL_FEATURES, *categorical_vectors],
            outputCol="features",
            handleInvalid="error",
        )
        classifier = RandomForestClassifier(
            featuresCol="features",
            labelCol="is_fraud",
            weightCol="class_weight",
            predictionCol="prediction",
            probabilityCol="probability",
            numTrees=num_trees,
            maxDepth=max_depth,
            maxBins=1024,
            seed=seed,
        )
        model = Pipeline(
            stages=[feature_engineering, *indexers, one_hot, assembler, classifier]
        ).fit(weighted_training)
        calibration_predictions = model.transform(calibration)
        operating_points = threshold_diagnostics(calibration_predictions)
        applied_threshold = float(operating_points["applied_threshold"])
        classifier_model: Any = model.stages[-1]
        classifier_model.setThresholds([1 - applied_threshold, applied_threshold])

        predictions = model.transform(evaluation)
        metrics = evaluate(predictions)

        settings.model_path.parent.mkdir(parents=True, exist_ok=True)
        model.write().overwrite().save(str(settings.model_path))

        metadata: dict[str, Any] = {
            "model_version": settings.model_version,
            "trained_at": datetime.now(UTC).isoformat(),
            "algorithm": "Spark RandomForestClassifier",
            "raw_features": list(FEATURE_COLUMNS),
            "numeric_model_features": list(NUMERIC_MODEL_FEATURES),
            "categorical_strategy": "StringIndexer + one-hot encoding",
            "num_trees": num_trees,
            "max_depth": max_depth,
            "seed": seed,
            "fraud_class_weight": fraud_weight,
            "training_rows": training.count(),
            "calibration_rows": calibration.count(),
            "validation_rows": evaluation.count(),
            "calibration_cutoff_unix_time": int(cutoff),
            "metrics": metrics,
            "threshold_diagnostics": operating_points,
        }
        settings.model_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        settings.model_metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        LOGGER.info(
            "Model training complete",
            extra={
                "model_path": settings.model_path,
                "metadata_path": settings.model_metadata_path,
                "area_under_pr": metrics["area_under_pr"],
                "fraud_recall": metrics["fraud_recall"],
            },
        )
        return metadata
    finally:
        spark.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-trees", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--env-file", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    train_model(
        settings,
        num_trees=args.num_trees,
        max_depth=args.max_depth,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
