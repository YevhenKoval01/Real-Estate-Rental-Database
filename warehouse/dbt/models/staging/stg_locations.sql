select
    location_id,
    city,
    region,
    country_code,
    batch_id,
    source_timestamp,
    record_fingerprint,
    processed_at
from {{ source('rental_staging', 'locations') }}
