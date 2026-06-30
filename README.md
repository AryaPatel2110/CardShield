# CardShield

CardShield is a streaming credit-card fraud detection project built with
PySpark, Kafka, Cassandra, FastAPI, and React. The repository includes the original
academic notebooks and production-oriented Python modules directly under
`src/`.

## Runtime flow

```text
Sparkov dataset
  -> leakage-safe preprocessing
  -> Spark Random Forest training and evaluation
  -> versioned model
  -> Kafka transaction topic
  -> Spark Structured Streaming scoring
  -> Cassandra time-bucketed query tables
```

Invalid Kafka events are sent to `transactions.dlq.v1`. Spark offsets are
checkpointed under `runtime/checkpoints`, and each prediction stores its model
version and fraud probability.

## Requirements

- Python 3.11
- Java 17
- Node.js 20 or newer
- Docker Desktop
- Approximately 3 GB of free disk space for the dataset and containers

On macOS:

```bash
brew install python@3.11 openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
```

## Dataset

Download the
[Credit Card Transactions Fraud Detection dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection/data)
and place these files under `data/`:

```text
data/fraudTrain.csv
data/fraudTest.csv
```

Using the Kaggle CLI:

```bash
kaggle datasets download \
  -d kartik2112/fraud-detection \
  -p data \
  --unzip
```

## Install

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[training,web,dev]"
cp .env.example .env
cd web && npm install && cd ..
```

## Prepare data and train

The preprocessing job fits categorical mappings only on `fraudTrain.csv`.
`fraudTest.csv` remains a later validation/replay period.

```bash
cardshield-preprocess
cardshield-train
```

For a quick pipeline check:

```bash
cardshield-preprocess --sample-size 5000
cardshield-train --num-trees 10 --max-depth 5
```

Do not treat a smoke-test model as release-ready. Review
`models/fraud_pipeline-metadata.json`, especially fraud recall, fraud precision,
PR-AUC, and the confusion matrix.

## Run locally

Start Kafka and Cassandra:

```bash
docker compose up -d kafka cassandra
docker compose run --rm kafka-init
```

Apply Cassandra migrations:

```bash
cardshield-migrate
```

Open four terminals with the virtual environment activated.

Terminal 1 — start scoring:

```bash
cardshield-score
```

Terminal 2 — replay transactions:

```bash
cardshield-produce --max-records 100
```

Terminal 3 — start the model and dashboard API:

```bash
cardshield-api
```

On macOS, if Java is not globally registered:

```bash
export JAVA_HOME="$(brew --prefix openjdk@17)"
cardshield-api
```

Terminal 4 — start the React website:

```bash
cd web
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The website includes:

- `/` — the CardShield landing page;
- `/dashboard` — live Cassandra metrics and recent model decisions;
- `/simulate` — held-out presets, synchronous inference, and a traced live
  Kafka-to-Spark transaction path;
- `/system` — runtime architecture, component health, model metrics, and
  documented tradeoffs.

The first API startup can take several seconds while Spark loads the model.
Each simulator result is written to Cassandra when storage is available, so it
will immediately become part of the dashboard.

Before a live presentation, run:

```bash
make demo-check
```

This fails fast when the trained model, release metrics, encoders, replay data,
or Docker command are missing. See [docs/DEMO.md](docs/DEMO.md) for the
three-minute presentation flow.

## Run the containerized stack

After preprocessing and training have created `data/clean_test.csv` and
`models/fraud_pipeline`:

```bash
docker compose --profile demo up --build
```

Open [http://localhost:3000](http://localhost:3000) for the containerized
website. Its Nginx server forwards API requests to the `api` service.

The `producer` service is under the `demo` profile because a production
deployment receives transactions from a payment system rather than replaying a
CSV.

## Commands

| Command | Purpose |
|---|---|
| `cardshield-preprocess` | Build train, validation, replay, and encoder artifacts |
| `cardshield-train` | Train and evaluate the Spark model |
| `cardshield-migrate` | Create production Cassandra tables |
| `cardshield-score` | Run the Structured Streaming scorer |
| `cardshield-produce` | Replay validated development transactions |
| `cardshield-api` | Serve model inference and dashboard endpoints |
| `make web` | Start the React development server |
| `make test` | Run unit tests |
| `make lint` | Run Ruff and strict MyPy |
| `make demo-check` | Verify that local demo artifacts are ready |

## Package structure

```text
src/
├── config.py                 # environment configuration
├── schemas.py                # versioned transaction contract
├── preprocessing.py          # leakage-safe dataset preparation
├── training.py               # Spark training and evaluation
├── producer.py               # idempotent Kafka replay producer
├── streaming_job.py          # Structured Streaming inference
├── model_service.py          # synchronous Spark inference for the API
├── api.py                    # prediction and dashboard HTTP endpoints
├── cassandra_repository.py   # idempotent persistence
├── migrate.py                # CQL migration runner
└── app_logging.py            # JSON service logs
web/                          # Vite + React website
```

## Production boundary

This code is production-oriented, but the included Compose stack is a
single-machine development environment. A real payment deployment still needs:

- multi-node, TLS-authenticated Kafka and Cassandra;
- durable remote Spark checkpoints;
- a model registry and approval workflow;
- payment-data tokenization and PCI DSS controls;
- authenticated operational interfaces;
- metrics, alerting, backups, disaster-recovery tests, and load tests;
- a model that passes agreed fraud recall and false-positive release gates.

See [docs/PRODUCTION.md](docs/PRODUCTION.md) for deployment gates.
