select
    agreement.rental_agreement_key,
    agreement.agreement_id,
    agreement.property_key,
    agreement.tenant_key,
    location.city,
    agreement.end_date,
    agreement.end_date - current_date as days_until_expiration,
    agreement.monthly_rent
from {{ ref('fact_rental_agreement') }} as agreement
inner join {{ ref('dim_location') }} as location
    on agreement.location_key = location.location_key
where agreement.end_date between current_date and current_date + 30
