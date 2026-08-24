with monthly_rents as (
    select
        agreement.location_key,
        location.city,
        location.region,
        date_trunc('month', agreement.start_date)::date as agreement_month,
        count(*) as agreement_count,
        avg(agreement.monthly_rent) as average_monthly_rent
    from {{ ref('fact_rental_agreement') }} as agreement
    inner join {{ ref('dim_location') }} as location
        on agreement.location_key = location.location_key
    group by
        agreement.location_key,
        location.city,
        location.region,
        date_trunc('month', agreement.start_date)::date
)
select
    location_key,
    city,
    region,
    agreement_month,
    agreement_count,
    round(average_monthly_rent, 2) as average_monthly_rent,
    round(
        average_monthly_rent
        - lag(average_monthly_rent) over (
            partition by location_key order by agreement_month
        ),
        2
    ) as rent_change_from_previous_month
from monthly_rents
