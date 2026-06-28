# Production readiness gates

The Compose environment is for development and staging. Promotion to a payment
environment requires every gate below to have an owner and recorded evidence.

## Model gate

- Time-based train/validation split is preserved.
- Encoders and feature transformations are fitted on training data only.
- Fraud precision, fraud recall, PR-AUC, confusion matrix, and calibration are
  reviewed.
- The decision threshold is approved against the cost of false positives and
  false negatives.
- Model version, dataset version, code revision, and metrics are registered.
- Shadow or canary comparison succeeds before promotion.

## Data contract gate

- The versioned event schema is published and compatibility-tested.
- Raw PAN, customer names, street addresses, and sensitive authentication data
  are absent from Kafka events and logs.
- Invalid events reach the dead-letter topic with an alert.
- Delayed ground-truth labels arrive through a separate feedback workflow.

## Reliability gate

- Kafka has at least three brokers and replication factor three.
- Cassandra is multi-node and replicated across failure domains.
- Spark checkpoints live in durable remote storage.
- Kafka replay and Cassandra writes are proven idempotent.
- Restart, broker-loss, database-loss, and checkpoint-recovery tests pass.
- Backups are restored in a scheduled disaster-recovery exercise.

## Security gate

- Kafka and Cassandra use TLS, authentication, and least-privilege authorization.
- Secrets come from a managed secrets service.
- Operational interfaces use organization authentication and least-privilege credentials.
- Images and dependencies are scanned before deployment.
- Payment-data handling has been reviewed against applicable PCI DSS controls.

## Operations gate

- Monitoring covers throughput, scoring latency, Kafka lag, invalid events,
  Cassandra errors, fraud rate, and feature drift.
- Alerts have runbooks, owners, and tested escalation paths.
- Capacity and load tests meet the agreed throughput and latency SLOs.
- Rollback is automated for both application and model versions.
