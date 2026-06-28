"""Replay validated transactions to Kafka for development and load testing."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import time
from collections.abc import Iterator
from pathlib import Path
from threading import Event
from typing import Any

import pandas as pd
from kafka import KafkaProducer

from app_logging import configure_logging
from config import Settings
from schemas import SchemaValidationError, TransactionEvent

LOGGER = logging.getLogger(__name__)


class TransactionProducer:
    """Kafka producer configured for acknowledged, idempotent writes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer = KafkaProducer(
            bootstrap_servers=list(settings.kafka_bootstrap_servers),
            client_id=f"{settings.kafka_client_id}-producer",
            acks="all",
            enable_idempotence=True,
            retries=10,
            key_serializer=lambda key: key.encode("utf-8"),
            value_serializer=lambda value: json.dumps(
                value,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    def send(self, event: TransactionEvent) -> Any:
        return self._producer.send(
            self._settings.kafka_input_topic,
            key=event.trans_num,
            value=event.to_dict(),
        )

    def flush(self) -> None:
        self._producer.flush(timeout=30)

    def close(self) -> None:
        self._producer.close(timeout=30)


def iter_replay_events(path: Path, *, chunk_size: int = 10_000) -> Iterator[TransactionEvent]:
    if not path.exists():
        raise FileNotFoundError(f"Replay dataset not found: {path}")

    for chunk in pd.read_csv(path, chunksize=chunk_size, low_memory=False):
        unnamed = [column for column in chunk.columns if column.startswith("Unnamed:")]
        if unnamed:
            chunk = chunk.drop(columns=unnamed)
        for row in chunk.to_dict(orient="records"):
            sanitized = {
                key: value
                for key, value in row.items()
                if not (isinstance(value, float) and pd.isna(value))
            }
            try:
                yield TransactionEvent.from_mapping(sanitized)
            except SchemaValidationError:
                LOGGER.exception(
                    "Skipping invalid replay event",
                    extra={"trans_num": sanitized.get("trans_num")},
                )


def replay(
    settings: Settings,
    *,
    loop: bool = False,
    max_records: int | None = None,
) -> int:
    producer = TransactionProducer(settings)
    stop_event = Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    sent = 0
    try:
        while not stop_event.is_set():
            for event in iter_replay_events(settings.replay_path):
                if stop_event.is_set():
                    break
                producer.send(event)
                sent += 1
                if sent % settings.producer_batch_size == 0:
                    producer.flush()
                    LOGGER.info("Published transaction batch", extra={"sent": sent})
                    time.sleep(settings.producer_interval_seconds)
                if max_records is not None and sent >= max_records:
                    stop_event.set()
                    break
            if not loop:
                break
        producer.flush()
        return sent
    finally:
        producer.close()
        LOGGER.info("Producer stopped", extra={"sent": sent})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--env-file", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    replay(settings, loop=args.loop, max_records=args.max_records)


if __name__ == "__main__":
    main()
