"""Fault-tolerant Spark Structured Streaming fraud scorer."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC
from pathlib import Path

from pyspark.ml import PipelineModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as functions
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from app_logging import configure_logging
from cassandra_repository import CassandraRepository
from config import Settings
from schemas import FEATURE_COLUMNS, ScoredTransaction, TransactionEvent

LOGGER = logging.getLogger(__name__)
SPARK_KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6"

TRANSACTION_SCHEMA = StructType(
    [
        StructField("schema_version", IntegerType()),
        StructField("trans_num", StringType()),
        StructField("amt", DoubleType()),
        StructField("lat", DoubleType()),
        StructField("long", DoubleType()),
        StructField("city_pop", IntegerType()),
        StructField("unix_time", LongType()),
        StructField("merch_lat", DoubleType()),
        StructField("merch_long", DoubleType()),
        StructField("merchant_label", IntegerType()),
        StructField("category_label", IntegerType()),
        StructField("gender_label", IntegerType()),
        StructField("job_label", IntegerType()),
        StructField("merchant", StringType()),
        StructField("category", StringType()),
        StructField("gender", StringType()),
        StructField("job", StringType()),
        StructField("trans_date_trans_time", StringType()),
        StructField("cc_num", LongType()),
        StructField("is_fraud", IntegerType()),
    ]
)


def create_spark_session() -> SparkSession:
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    return (
        SparkSession.builder.appName("CardShieldStreamingScorer")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.jars.packages", SPARK_KAFKA_PACKAGE)
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )


def valid_transaction_condition() -> Column:
    required = [
        functions.col(f"transaction.{column}").isNotNull()
        for column in ("trans_num", *FEATURE_COLUMNS)
    ]
    condition = required[0]
    for requirement in required[1:]:
        condition = condition & requirement
    return (
        condition
        & (functions.col("transaction.schema_version") == 1)
        & (functions.col("transaction.amt") >= 0)
        & functions.col("transaction.lat").between(-90, 90)
        & functions.col("transaction.merch_lat").between(-90, 90)
        & functions.col("transaction.long").between(-180, 180)
        & functions.col("transaction.merch_long").between(-180, 180)
    )


def write_prediction_batch(
    batch: DataFrame,
    _batch_id: int,
    *,
    settings: Settings,
) -> None:
    """Persist one micro-batch; deterministic Kafka timestamps make retries idempotent."""
    if batch.isEmpty():
        return

    with CassandraRepository(settings) as repository:
        count = 0
        for row in batch.toLocalIterator():
            payload = row.asDict(recursive=True)
            scored_at = payload.pop("kafka_timestamp")
            if scored_at.tzinfo is None:
                scored_at = scored_at.replace(tzinfo=UTC)

            prediction = int(payload.pop("prediction"))
            fraud_probability = float(payload.pop("fraud_probability"))
            transaction = TransactionEvent.from_mapping(payload)
            repository.write_scored(
                ScoredTransaction(
                    transaction=transaction,
                    prediction=prediction,
                    fraud_probability=fraud_probability,
                    model_version=settings.model_version,
                    scored_at=scored_at,
                )
            )
            count += 1
        LOGGER.info("Persisted scoring batch", extra={"transactions": count})


def run_stream(settings: Settings) -> None:
    if not settings.model_path.exists():
        raise FileNotFoundError(f"Model not found: {settings.model_path}")

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    model = PipelineModel.load(str(settings.model_path))

    raw = (
        spark.readStream.format("kafka")
        .option(
            "kafka.bootstrap.servers",
            ",".join(settings.kafka_bootstrap_servers),
        )
        .option("subscribe", settings.kafka_input_topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = raw.select(
        "key",
        "value",
        "timestamp",
        functions.from_json(
            functions.col("value").cast("string"),
            TRANSACTION_SCHEMA,
            {"mode": "PERMISSIVE"},
        ).alias("transaction"),
    )
    is_valid = functions.coalesce(valid_transaction_condition(), functions.lit(False))

    invalid = parsed.filter(~is_valid).select("key", "value")
    valid = parsed.filter(is_valid).select(
        functions.col("timestamp").alias("kafka_timestamp"),
        "transaction.*",
    )

    predictions = (
        model.transform(valid)
        .withColumn(
            "fraud_probability",
            vector_to_array(functions.col("probability"))[1],
        )
        .select(
            "kafka_timestamp",
            "trans_num",
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
            "merchant",
            "category",
            "gender",
            "job",
            "trans_date_trans_time",
            "cc_num",
            "is_fraud",
            "schema_version",
            "prediction",
            "fraud_probability",
        )
    )

    settings.checkpoint_path.mkdir(parents=True, exist_ok=True)
    scored_query = (
        predictions.writeStream.foreachBatch(
            lambda frame, batch_id: write_prediction_batch(
                frame,
                batch_id,
                settings=settings,
            )
        )
        .option(
            "checkpointLocation",
            str(settings.checkpoint_path / "scored"),
        )
        .trigger(processingTime=f"{settings.stream_trigger_seconds} seconds")
        .queryName("cardshield-scoring")
        .start()
    )

    dead_letter_query = (
        invalid.writeStream.format("kafka")
        .option(
            "kafka.bootstrap.servers",
            ",".join(settings.kafka_bootstrap_servers),
        )
        .option("topic", settings.kafka_dead_letter_topic)
        .option(
            "checkpointLocation",
            str(settings.checkpoint_path / "dead-letter"),
        )
        .queryName("cardshield-dead-letter")
        .start()
    )

    LOGGER.info(
        "Streaming scorer started",
        extra={
            "input_topic": settings.kafka_input_topic,
            "dead_letter_topic": settings.kafka_dead_letter_topic,
            "model_version": settings.model_version,
        },
    )
    try:
        spark.streams.awaitAnyTermination()
    finally:
        scored_query.stop()
        dead_letter_query.stop()
        spark.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    run_stream(settings)


if __name__ == "__main__":
    main()
