select
    property_id,
    location_id,
    owner_id,
    property_type,
    bedrooms,
    size_sqm,
    monthly_rent,
    currency,
    batch_id,
    source_timestamp,
    record_fingerprint,
    processed_at
from {{ source('rental_staging', 'properties') }}
