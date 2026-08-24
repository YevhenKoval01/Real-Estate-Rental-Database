select
    property.location_key,
    location.city,
    location.region,
    count(*) as property_count,
    round(avg(property.monthly_rent / nullif(property.size_sqm, 0)), 2) as average_rent_per_sqm
from {{ ref('dim_property') }} as property
inner join {{ ref('dim_location') }} as location
    on property.location_key = location.location_key
group by property.location_key, location.city, location.region
