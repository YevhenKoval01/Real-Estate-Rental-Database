# Known limitations

- Synthetic files model a source system; there is no external API, CDC stream, or production identity model.
- Missing input rows do not imply deletion because no tombstone/full-snapshot contract exists.
- Shared Python quality evaluation collects records on the Spark driver, and local outputs are coalesced. The performance profile is a local benchmark, not big-data scale.
- PostgreSQL staging is current state. Only property attributes covered by the dbt snapshot retain SCD2 history.
- The deterministic sample calendar begins in 2024. The rolling `current_date` expiration mart can legitimately be empty when the project is run after those agreements end; use a larger/current source profile before demonstrating that visual.
- Dimensions/facts rebuild as dbt tables. Incremental dbt materializations are unnecessary at the verified scale and remain future optimization work.
- Airflow standalone uses local credentials, local logs, and one host. Production secrets, remote logging, HA metadata, alerting, and executor design are out of scope.
- The Power BI semantic model passed structural validation only. Desktop refresh, DAX execution, visual layout, accessibility, gateway configuration, and Fabric publication were not verified.
- The index result is a warm-cache microbenchmark for one selective query and cannot be generalized to all workloads.
- Legacy Oracle and SQL Server files are preserved but not executed by the platform CI.
