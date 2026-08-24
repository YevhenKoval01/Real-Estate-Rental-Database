# Incremental and idempotent processing

Each normalized record receives a SHA-256 fingerprint of canonical business values. Batch ID, source timestamp, fingerprint, and processing timestamp are excluded from that hash, so a replay with new operational metadata remains unchanged.

For every entity, the PostgreSQL loader compares the incoming primary key and fingerprint with current staging state:

| Incoming state | Action | Audit metric |
|---|---|---|
| Key absent | Insert | `inserted_count` |
| Key present, different fingerprint | Update current row and metadata | `updated_count` |
| Key present, same fingerprint | No write | `skipped_count` |

All entity writes and rejection writes for a load use one database transaction. Rejection uniqueness by batch, record type, source ID, and reason makes retries safe. Reusing a batch ID resets and completes the same audit row rather than adding a second run.

The generator is extension-stable: increasing `dataset_size` retains existing business values and appends stable IDs. Decreasing it does **not** delete staging rows. Source absence is treated as “not observed,” not a deletion request, because this simulated source provides no tombstones or authoritative full-snapshot contract. dbt's property snapshot is configured to invalidate hard deletes if a deliberate staging deletion is introduced later.

Changing property rent updates the current `staging.properties` row and related agreement/payment values. The dbt `property_history` check snapshot versions changed property attributes as SCD Type 2 history, while facts and current dimensions rebuild deterministically from staging.
