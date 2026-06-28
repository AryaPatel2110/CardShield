"""Apply CardShield Cassandra schema migrations."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy

from app_logging import configure_logging
from cassandra_repository import _safe_identifier
from config import Settings

LOGGER = logging.getLogger(__name__)


def apply_migrations(settings: Settings, migration_dir: Path | None = None) -> int:
    directory = migration_dir or settings.project_root / "migrations"
    files = sorted(directory.glob("*.cql"))
    if not files:
        raise FileNotFoundError(f"No CQL migrations found in {directory}")

    auth_provider = None
    if settings.cassandra_username and settings.cassandra_password:
        auth_provider = PlainTextAuthProvider(
            username=settings.cassandra_username,
            password=settings.cassandra_password,
        )
    cluster = Cluster(
        list(settings.cassandra_hosts),
        port=settings.cassandra_port,
        auth_provider=auth_provider,
        protocol_version=5,
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=settings.cassandra_local_dc),
    )
    session = cluster.connect()
    keyspace = _safe_identifier(settings.cassandra_keyspace, name="keyspace")
    applied = 0
    try:
        for migration in files:
            content = migration.read_text(encoding="utf-8").replace("bigdata", keyspace)
            statements = [
                statement.strip() for statement in content.split(";") if statement.strip()
            ]
            for statement in statements:
                session.execute(statement)
            applied += 1
            LOGGER.info("Applied Cassandra migration", extra={"migration": migration.name})
        return applied
    finally:
        session.shutdown()
        cluster.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--migration-dir", type=Path, default=None)
    args = parser.parse_args()

    settings = Settings.from_env(args.env_file)
    configure_logging(settings.log_level)
    apply_migrations(settings, args.migration_dir)


if __name__ == "__main__":
    main()
