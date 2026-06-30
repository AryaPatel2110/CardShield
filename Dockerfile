FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/java \
    CARDSHIELD_SPARK_IVY_DIR=/opt/spark-ivy \
    PATH="/opt/java/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y openjdk-17-jre-headless procps \
    && ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")" /opt/java \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[training,web]"

# Cache the Structured Streaming Kafka connector in the image so a prepared
# live demo does not depend on Maven Central at container startup.
RUN mkdir -p "${CARDSHIELD_SPARK_IVY_DIR}" \
    && python -c "from pyspark.sql import SparkSession; spark = SparkSession.builder.master('local[1]').config('spark.ui.enabled', 'false').config('spark.jars.ivy', '${CARDSHIELD_SPARK_IVY_DIR}').config('spark.jars.packages', 'org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6').getOrCreate(); spark.stop()"

COPY migrations ./migrations
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 cardshield \
    && mkdir -p /app/runtime /app/models /app/data \
    && chown -R cardshield:cardshield /app "${CARDSHIELD_SPARK_IVY_DIR}"

USER cardshield

CMD ["cardshield-score"]
