# Data-quality strategy

Quality is evaluated per record before Silver. Invalid rows are never silently discarded: they are written to batch-partitioned JSON Lines and loaded to `staging.rejected_records` with the raw record, record type, source identifier, batch ID, code, explanation, and UTC processing time.

Rules cover required fields; identifier uniqueness; ISO dates and timezone-aware source timestamps; supported property, agreement, payment, currency, and country values; sane bedrooms, sizes, rents, and amounts; agreement date ordering; parent-key existence; and payment due dates inside agreement bounds. Text normalization deliberately accepts harmless case and whitespace differences.

Representative codes include `MISSING_REQUIRED_FIELD`, `DUPLICATE_IDENTIFIER`, `INVALID_DATE`, `INVALID_AGREEMENT_RANGE`, `INVALID_PROPERTY_SIZE`, `INVALID_RENT`, and the `ORPHAN_*` relationship codes. The deterministic generator can activate its nine known scenarios with `--quality-issues 1..9`; all nine source mutations result in eight quarantined rows because inconsistent location casing is valid after normalization.

The audit invariant is:

```text
input_count = accepted_count + rejected_count
accepted_count = inserted_count + updated_count + skipped_count
```

dbt adds warehouse checks for primary-key uniqueness, non-null critical fields, relationships, accepted values, agreement dates, payment financial consistency, and occupancy rates between zero and one. A failed Python step exits non-zero; a load failure records `FAILED` with its message when the audit database remains reachable; a failed dbt test stops the DAG before summary publication.
