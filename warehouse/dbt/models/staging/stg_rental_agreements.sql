select
    agreement_id,
    property_id,
    tenant_id,
    start_date,
    end_date,
    monthly_rent,
    status,
    batch_id,
    source_timestamp,
    record_fingerprint,
    processed_at
from {{ source('rental_staging', 'rental_agreements') }}
