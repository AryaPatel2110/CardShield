FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/opt/java \
    PATH="/opt/java/bin:${PATH}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y openjdk-17-jre-headless procps \
    && ln -s "$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")" /opt/java \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[training,web]"

COPY migrations ./migrations
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 cardshield \
    && mkdir -p /app/runtime /app/models /app/data \
    && chown -R cardshield:cardshield /app

USER cardshield

CMD ["cardshield-score"]
