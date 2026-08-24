select
    agreement.agreement_id,
    agreement.property_id,
    agreement.tenant_id,
    property.owner_id,
    property.location_id,
    agreement.start_date,
    agreement.end_date,
    agreement.monthly_rent,
    agreement.status,
    property.property_type,
    property.bedrooms,
    property.size_sqm,
    property.currency,
    location.city,
    location.region,
    owner.full_name as owner_name,
    tenant.full_name as tenant_name
from {{ ref('stg_rental_agreements') }} as agreement
inner join {{ ref('stg_properties') }} as property
    on agreement.property_id = property.property_id
inner join {{ ref('stg_locations') }} as location
    on property.location_id = location.location_id
inner join {{ ref('stg_owners') }} as owner
    on property.owner_id = owner.owner_id
inner join {{ ref('stg_tenants') }} as tenant
    on agreement.tenant_id = tenant.tenant_id
