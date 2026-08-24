{% snapshot property_history %}

{{
    config(
        target_schema='analytics_snapshots',
        unique_key='property_id',
        strategy='check',
        check_cols=[
            'location_id',
            'owner_id',
            'property_type',
            'bedrooms',
            'size_sqm',
            'monthly_rent',
            'currency'
        ],
        invalidate_hard_deletes=True
    )
}}

select
    property_id,
    location_id,
    owner_id,
    property_type,
    bedrooms,
    size_sqm,
    monthly_rent,
    currency,
    source_timestamp,
    processed_at
from {{ source('rental_staging', 'properties') }}

{% endsnapshot %}
