select
    tenant_id,
    full_name,
    email,
    batch_id,
    source_timestamp,
    record_fingerprint,
    processed_at
from {{ source('rental_staging', 'tenants') }}
