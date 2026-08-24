select
    md5(property.property_id) as property_key,
    property.property_id,
    location.location_key,
    owner.owner_key,
    property.property_type,
    property.bedrooms,
    property.size_sqm,
    property.monthly_rent,
    property.currency
from {{ ref('stg_properties') }} as property
inner join {{ ref('dim_location') }} as location
    on property.location_id = location.location_id
inner join {{ ref('dim_owner') }} as owner
    on property.owner_id = owner.owner_id
