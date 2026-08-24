select
    md5(location_id) as location_key,
    location_id,
    city,
    region,
    country_code
from {{ ref('stg_locations') }}
