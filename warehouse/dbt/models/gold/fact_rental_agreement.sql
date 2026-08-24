select
    md5(agreement.agreement_id) as rental_agreement_key,
    agreement.agreement_id,
    property.property_key,
    property.location_key,
    property.owner_key,
    tenant.tenant_key,
    to_char(agreement.start_date, 'YYYYMMDD')::integer as start_date_key,
    to_char(agreement.end_date, 'YYYYMMDD')::integer as end_date_key,
    agreement.start_date,
    agreement.end_date,
    agreement.monthly_rent,
    agreement.status,
    (agreement.end_date - agreement.start_date + 1) as agreement_days
from {{ ref('stg_rental_agreements') }} as agreement
inner join {{ ref('dim_property') }} as property
    on agreement.property_id = property.property_id
inner join {{ ref('dim_tenant') }} as tenant
    on agreement.tenant_id = tenant.tenant_id
