select
    payment_id,
    agreement_id,
    due_date,
    payment_date,
    amount,
    status,
    batch_id,
    source_timestamp,
    record_fingerprint,
    processed_at
from {{ source('rental_staging', 'payments') }}
