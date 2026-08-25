# Roadmap

The portfolio scope is complete. Plausible production extensions, intentionally not claimed as implemented, are:

1. Add an authoritative source contract with deletion/tombstone semantics and schema evolution.
2. Move quality evaluation and bulk loading to partition-aware Spark/PostgreSQL operations for materially larger data.
3. Add incremental dbt materializations only after warehouse profiling shows rebuild cost is significant.
4. Validate the semantic model in Power BI Desktop, source-control reviewed PBIR report pages, and add accessibility checks.
5. Deploy Airflow with a supported production executor, secret backend, remote logs, monitoring, and alerts.
6. Add historical benchmark runs on controlled hardware and regression thresholds after enough stable samples exist.
