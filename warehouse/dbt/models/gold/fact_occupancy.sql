select
    md5(agreement.agreement_id || ':' || date_dimension.date_day::text) as occupancy_key,
    agreement.rental_agreement_key,
    agreement.property_key,
    agreement.location_key,
    agreement.tenant_key,
    date_dimension.date_key,
    date_dimension.date_day,
    1 as occupied_day
from {{ ref('fact_rental_agreement') }} as agreement
inner join {{ ref('dim_date') }} as date_dimension
    on date_dimension.date_day between agreement.start_date and agreement.end_date
