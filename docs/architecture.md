# Platform architecture

## System view

```mermaid
flowchart LR
    subgraph Source[Source simulation]
        GEN[Deterministic Python generator]
        BAD[Configurable quality scenarios]
    end
    subgraph Lake[Local file layers]
        RAW[Source CSV / JSONL]
        BRONZE[Bronze immutable-shape copy]
        SILVER[Silver typed Parquet]
        REJECT[Rejected JSONL]
    end
    subgraph Warehouse[PostgreSQL 16]
        STAGE[Current-state staging]
        AUDIT[Runs and rejection audit]
        GOLD[dbt dimensions and facts]
        MARTS[dbt analytical marts]
        HISTORY[Property SCD2 snapshot]
    end
    subgraph Consumption[Consumption and operations]
        PBI[Power BI TMDL semantic model]
        AF[Airflow DAG]
        LOGS[JSON operational logs]
    end

    GEN --> RAW --> BRONZE
    BAD --> RAW
    BRONZE --> SILVER --> STAGE
    BRONZE --> REJECT --> AUDIT
    STAGE --> GOLD --> MARTS --> PBI
    STAGE --> HISTORY
    AF -. orchestrates .-> GEN
    AF -. orchestrates .-> GOLD
    GEN --> LOGS
    GOLD --> LOGS
```

The design uses one tool per clear responsibility. Python owns deterministic source simulation, shared business rules, incremental loading, and operational commands. PySpark supplies typed Parquet transformation. PostgreSQL is the durable runtime. dbt owns warehouse SQL, documentation, testing, and history. Airflow schedules the existing commands; it does not duplicate pipeline logic. Power BI consumes only tested Gold facts/marts.

## Dimensional model

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_OCCUPANCY : date_key
    DIM_LOCATION ||--o{ DIM_PROPERTY : location_key
    DIM_OWNER ||--o{ DIM_PROPERTY : owner_key
    DIM_PROPERTY ||--o{ FACT_RENTAL_AGREEMENT : property_key
    DIM_TENANT ||--o{ FACT_RENTAL_AGREEMENT : tenant_key
    FACT_RENTAL_AGREEMENT ||--o{ FACT_PAYMENT : rental_agreement_key
    FACT_RENTAL_AGREEMENT ||--o{ FACT_OCCUPANCY : rental_agreement_key
    DIM_LOCATION ||--o{ FACT_PAYMENT : location_key
```

Facts deliberately retain commonly filtered dimension keys. The current property dimension supports current-state analysis; `analytics_snapshots.property_history` separately retains checked property changes as SCD Type 2 history.

## Security and deployment boundary

Compose defaults are explicitly local-development credentials. Secrets come from environment variables and are never stored in TMDL, generated evidence, logs, or Git. Airflow standalone and the single-host Spark runtime demonstrate the workflow but are not a production deployment topology.
