"""Query-oriented Cassandra persistence for scored transactions."""

from __future__ import annotations

import re
import zlib
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy

from config import Settings
from schemas import ScoredTransaction

SHARD_COUNT = 16
_IDENTIFIER = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


def _safe_identifier(value: str, *, name: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid Cassandra {name}: {value!r}")
    return value


def transaction_shard(transaction_id: str) -> int:
    """Return a stable shard that spreads each day across Cassandra nodes."""
    return zlib.crc32(transaction_id.encode("utf-8")) % SHARD_COUNT


class CassandraRepository:
    """Own Cassandra connections and idempotent scored-transaction writes."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        keyspace = _safe_identifier(settings.cassandra_keyspace, name="keyspace")

        auth_provider = None
        if settings.cassandra_username and settings.cassandra_password:
            auth_provider = PlainTextAuthProvider(
                username=settings.cassandra_username,
                password=settings.cassandra_password,
            )

        self._cluster = Cluster(
            list(settings.cassandra_hosts),
            port=settings.cassandra_port,
            auth_provider=auth_provider,
            protocol_version=5,
            load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=settings.cassandra_local_dc),
        )
        self._session = self._cluster.connect(keyspace)
        self._prepare_statements()

    @property
    def session(self) -> Session:
        return self._session

    def _prepare_statements(self) -> None:
        self._insert_transaction = self._session.prepare(
            """
            INSERT INTO transactions_by_day (
                transaction_day, shard, inserted_at, trans_num,
                merchant, category, amt, is_fraud, is_fraud_prediction,
                fraud_probability, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._insert_alert = self._session.prepare(
            """
            INSERT INTO fraud_alerts_by_day (
                alert_day, shard, inserted_at, trans_num,
                merchant, category, amt, fraud_probability, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )

    def write_scored(self, scored: ScoredTransaction) -> None:
        transaction = scored.transaction
        day = scored.scored_at.date()
        shard = transaction_shard(transaction.trans_num)
        amount = Decimal(str(transaction.amt))

        self._session.execute(
            self._insert_transaction,
            (
                day,
                shard,
                scored.scored_at,
                transaction.trans_num,
                transaction.merchant,
                transaction.category,
                amount,
                transaction.is_fraud,
                scored.prediction,
                scored.fraud_probability,
                scored.model_version,
            ),
        )

        if scored.prediction == 1:
            self._session.execute(
                self._insert_alert,
                (
                    day,
                    shard,
                    scored.scored_at,
                    transaction.trans_num,
                    transaction.merchant,
                    transaction.category,
                    amount,
                    scored.fraud_probability,
                    scored.model_version,
                ),
            )

    def write_many(self, transactions: Iterable[ScoredTransaction]) -> int:
        count = 0
        for transaction in transactions:
            self.write_scored(transaction)
            count += 1
        return count

    def recent_transactions(
        self,
        *,
        limit: int = 200,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Read the newest transactions across the application's day shards."""
        if limit < 1:
            raise ValueError("limit must be positive")
        if days < 1:
            raise ValueError("days must be positive")

        statement = self._session.prepare(
            """
            SELECT inserted_at, trans_num, merchant, category, amt,
                   is_fraud, is_fraud_prediction, fraud_probability, model_version
            FROM transactions_by_day
            WHERE transaction_day = ? AND shard = ?
            LIMIT ?
            """
        )
        rows: list[dict[str, Any]] = []
        today = datetime.now(UTC).date()
        for offset in range(days):
            transaction_day: date = today - timedelta(days=offset)
            for shard in range(SHARD_COUNT):
                result = self._session.execute(statement, (transaction_day, shard, limit))
                rows.extend(dict(row._asdict()) for row in result)

        rows.sort(key=lambda row: row["inserted_at"], reverse=True)
        return rows[:limit]

    def close(self) -> None:
        self._session.shutdown()
        self._cluster.shutdown()

    def __enter__(self) -> CassandraRepository:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
