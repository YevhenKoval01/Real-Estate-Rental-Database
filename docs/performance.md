# Reproducible performance report

## Scope and method

The benchmark targets a real drill-through pattern: retrieving the three scheduled payments for one agreement in due-date order. It uses PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` and records every plan plus the median of repeated execution times.

The measured profile used seed 42, 5,000 properties, 5,000 agreements, and 15,000 payments (30,010 total source records). It ran on PostgreSQL 16.10 in Docker Desktop 29.6.2 on the project maintainer's Windows development machine. The performance expansion pipeline completed in 32.787 seconds; it followed the 13-property smoke state, so its load metrics were 29,922 inserts, 5 updates, and 83 skips rather than a clean full-load claim.

## Measured result

Measurement timestamp: 2026-08-25 13:44 UTC. Eleven warm executions were collected for each state.

| State | Median execution | Plan | Shared buffers in captured plan |
|---|---:|---|---:|
| Before project indexes | 0.968 ms | sequential scan + sort | 334 hits |
| After project indexes | 0.047 ms | `idx_payments_agreement_due_date` index scan | 4 hits |

For this exact selective query, the measured median was 95.14% lower. This is a sub-millisecond, warm-cache microbenchmark—not an application SLA or proof that every analytical query becomes faster. Hardware, cache state, PostgreSQL settings, cardinality, and data distribution can change the result.

## Reproduce

```powershell
docker compose down --volumes
docker compose --env-file config/performance.env.example up --detach --wait postgres
docker compose --env-file config/performance.env.example --profile pipeline run --build --rm pipeline run --batch-id performance-5000
docker compose --env-file config/performance.env.example --profile pipeline run --rm pipeline benchmark --iterations 11
Get-Content data/benchmark/index-benchmark.json
```

The benchmark drops and restores only the four indexes owned by migration `003_analytics_indexes.sql`. Its JSON artifact is intentionally ignored because timings are machine-specific. The indexes support agreement payment drill-through, location inventory joins, property/agreement joins, and active-agreement expiration searches.

At this size Spark warned that the single payment task exceeded its recommended serialized task size. That supports the documented limit: the current shared Python quality evaluation and coalesced local Parquet writes are suitable for portfolio-scale local data, not distributed high-volume processing.
