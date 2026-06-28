# Local setup

Run every command from the repository root.

## 1. Configure Python and Java

```bash
brew install python@3.11 openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[training,web,dev]"
cp .env.example .env
cd web
npm install
cd ..
```

## 2. Add data

Download the
[Sparkov Kaggle dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection/data)
and verify:

```bash
ls data/fraudTrain.csv data/fraudTest.csv
```

## 3. Build model artifacts

```bash
cardshield-preprocess
cardshield-train
```

Expected outputs:

```text
data/clean_train.csv
data/clean_validation.csv
data/clean_test.csv
models/encoders/categories-v1.json
models/fraud_pipeline/
models/fraud_pipeline-metadata.json
```

## 4. Start infrastructure

```bash
docker compose up -d kafka cassandra
docker compose run --rm kafka-init
cardshield-migrate
```

Check service state:

```bash
docker compose ps
```

## 5. Run applications

Use separate terminals:

```bash
cardshield-score
```

```bash
cardshield-produce --max-records 100
```

```bash
cardshield-api
```

```bash
cd web
npm run dev
```

Open <http://localhost:5173>. Use `/simulate` to score a transaction and
`/dashboard` to view predictions stored in Cassandra.

## 6. Verify

```bash
docker compose exec cassandra cqlsh -e \
  "SELECT * FROM bigdata.transactions_by_day LIMIT 10;"
```

Malformed events are written to `transactions.dlq.v1`.

Verify the API separately at <http://localhost:8000/api/health> and its
interactive documentation at <http://localhost:8000/docs>.

## 7. Stop

Stop foreground commands with `Ctrl+C`, then:

```bash
docker compose down
```
