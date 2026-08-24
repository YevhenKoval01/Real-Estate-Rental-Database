FROM apache/airflow:2.11.2-python3.12

USER root

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

RUN apt-get update \
    && apt-get install --no-install-recommends --yes openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/rental-venv \
    && chown -R airflow:root /opt/rental-venv

USER airflow
ENV PATH=/opt/rental-venv/bin:${PATH}
WORKDIR /app

COPY --chown=airflow:root pyproject.toml README.md ./
COPY --chown=airflow:root src ./src
COPY --chown=airflow:root warehouse/dbt ./warehouse/dbt
COPY --chown=airflow:root airflow/dags /opt/airflow/dags

RUN python -m pip install --no-cache-dir ".[warehouse]" \
    && python -m pip check \
    && /usr/local/bin/python -m pip check \
    && mkdir -p /app/data
