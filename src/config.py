"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when application configuration is invalid."""


def _read_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _read_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a number") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _read_hosts(name: str, default: str) -> tuple[str, ...]:
    hosts = tuple(host.strip() for host in os.getenv(name, default).split(",") if host.strip())
    if not hosts:
        raise ConfigurationError(f"{name} must contain at least one host")
    return hosts


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration shared by training, streaming, persistence, and UI."""

    project_root: Path = field(default_factory=Path.cwd)

    kafka_bootstrap_servers: tuple[str, ...] = ("localhost:9092",)
    kafka_input_topic: str = "transactions.v1"
    kafka_dead_letter_topic: str = "transactions.dlq.v1"
    kafka_consumer_group: str = "cardshield-scorer-v1"
    kafka_client_id: str = "cardshield"
    kafka_starting_offsets: str = "latest"

    cassandra_hosts: tuple[str, ...] = ("127.0.0.1",)
    cassandra_port: int = 9042
    cassandra_keyspace: str = "bigdata"
    cassandra_local_dc: str = "datacenter1"
    cassandra_username: str | None = None
    cassandra_password: str | None = None

    model_path: Path = Path("models/fraud_pipeline")
    model_version: str = "local-dev"
    checkpoint_path: Path = Path("runtime/checkpoints/fraud-scorer")

    raw_train_path: Path = Path("data/fraudTrain.csv")
    raw_test_path: Path = Path("data/fraudTest.csv")
    processed_train_path: Path = Path("data/clean_train.csv")
    processed_validation_path: Path = Path("data/clean_validation.csv")
    replay_path: Path = Path("data/clean_test.csv")
    encoder_path: Path = Path("models/encoders/categories-v1.json")
    legacy_encoder_path: Path = Path("models/encoders/LE_model_v1.pkl")
    model_metadata_path: Path = Path("models/fraud_pipeline-metadata.json")

    stream_trigger_seconds: int = 5
    producer_interval_seconds: float = 3.0
    producer_batch_size: int = 10
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_origins: tuple[str, ...] = ("http://localhost:5173",)

    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> Settings:
        """Load settings from an optional dotenv file and process environment."""
        if env_file is not None:
            load_dotenv(env_file)
        else:
            load_dotenv()

        root = Path(os.getenv("CARDSHIELD_PROJECT_ROOT", Path.cwd())).expanduser().resolve()

        def project_path(name: str, default: str) -> Path:
            configured = Path(os.getenv(name, default)).expanduser()
            return configured if configured.is_absolute() else root / configured

        username = os.getenv("CARDSHIELD_CASSANDRA_USERNAME") or None
        password = os.getenv("CARDSHIELD_CASSANDRA_PASSWORD") or None
        if bool(username) != bool(password):
            raise ConfigurationError(
                "CARDSHIELD_CASSANDRA_USERNAME and "
                "CARDSHIELD_CASSANDRA_PASSWORD must be set together"
            )
        starting_offsets = os.getenv("CARDSHIELD_KAFKA_STARTING_OFFSETS", "latest")
        if starting_offsets not in {"earliest", "latest"}:
            raise ConfigurationError(
                "CARDSHIELD_KAFKA_STARTING_OFFSETS must be earliest or latest"
            )

        return cls(
            project_root=root,
            kafka_bootstrap_servers=_read_hosts(
                "CARDSHIELD_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
            ),
            kafka_input_topic=os.getenv("CARDSHIELD_KAFKA_INPUT_TOPIC", "transactions.v1"),
            kafka_dead_letter_topic=os.getenv(
                "CARDSHIELD_KAFKA_DEAD_LETTER_TOPIC", "transactions.dlq.v1"
            ),
            kafka_consumer_group=os.getenv(
                "CARDSHIELD_KAFKA_CONSUMER_GROUP", "cardshield-scorer-v1"
            ),
            kafka_client_id=os.getenv("CARDSHIELD_KAFKA_CLIENT_ID", "cardshield"),
            kafka_starting_offsets=starting_offsets,
            cassandra_hosts=_read_hosts("CARDSHIELD_CASSANDRA_HOSTS", "127.0.0.1"),
            cassandra_port=_read_int("CARDSHIELD_CASSANDRA_PORT", 9042),
            cassandra_keyspace=os.getenv("CARDSHIELD_CASSANDRA_KEYSPACE", "bigdata"),
            cassandra_local_dc=os.getenv(
                "CARDSHIELD_CASSANDRA_LOCAL_DC",
                "datacenter1",
            ),
            cassandra_username=username,
            cassandra_password=password,
            model_path=project_path("CARDSHIELD_MODEL_PATH", "models/fraud_pipeline"),
            model_version=os.getenv("CARDSHIELD_MODEL_VERSION", "local-dev"),
            checkpoint_path=project_path(
                "CARDSHIELD_CHECKPOINT_PATH", "runtime/checkpoints/fraud-scorer"
            ),
            raw_train_path=project_path("CARDSHIELD_RAW_TRAIN_PATH", "data/fraudTrain.csv"),
            raw_test_path=project_path("CARDSHIELD_RAW_TEST_PATH", "data/fraudTest.csv"),
            processed_train_path=project_path(
                "CARDSHIELD_PROCESSED_TRAIN_PATH", "data/clean_train.csv"
            ),
            processed_validation_path=project_path(
                "CARDSHIELD_PROCESSED_VALIDATION_PATH",
                "data/clean_validation.csv",
            ),
            replay_path=project_path("CARDSHIELD_REPLAY_PATH", "data/clean_test.csv"),
            encoder_path=project_path(
                "CARDSHIELD_ENCODER_PATH",
                "models/encoders/categories-v1.json",
            ),
            legacy_encoder_path=project_path(
                "CARDSHIELD_LEGACY_ENCODER_PATH",
                "models/encoders/LE_model_v1.pkl",
            ),
            model_metadata_path=project_path(
                "CARDSHIELD_MODEL_METADATA_PATH",
                "models/fraud_pipeline-metadata.json",
            ),
            stream_trigger_seconds=_read_int("CARDSHIELD_STREAM_TRIGGER_SECONDS", 5),
            producer_interval_seconds=_read_float("CARDSHIELD_PRODUCER_INTERVAL_SECONDS", 3.0),
            producer_batch_size=_read_int("CARDSHIELD_PRODUCER_BATCH_SIZE", 10),
            api_host=os.getenv("CARDSHIELD_API_HOST", "0.0.0.0"),
            api_port=_read_int("CARDSHIELD_API_PORT", 8000),
            web_origins=_read_hosts(
                "CARDSHIELD_WEB_ORIGINS",
                "http://localhost:5173",
            ),
            log_level=os.getenv("CARDSHIELD_LOG_LEVEL", "INFO").upper(),
        )
