with calendar_month as (
    select
        month_start_date,
        count(*) as calendar_days
    from {{ ref('dim_date') }}
    group by month_start_date
),
inventory as (
    select
        location_key,
        count(*) as property_count
    from {{ ref('dim_property') }}
    group by location_key
),
occupied as (
    select
        location_key,
        date_trunc('month', date_day)::date as month_start_date,
        sum(occupied_day) as occupied_property_days
    from {{ ref('fact_occupancy') }}
    group by location_key, date_trunc('month', date_day)::date
)
select
    location.location_key,
    location.city,
    location.region,
    calendar_month.month_start_date,
    coalesce(occupied.occupied_property_days, 0) as occupied_property_days,
    inventory.property_count * calendar_month.calendar_days as available_property_days,
    round(
        coalesce(occupied.occupied_property_days, 0)::numeric
        / nullif(inventory.property_count * calendar_month.calendar_days, 0),
        4
    ) as occupancy_rate
from inventory
inner join {{ ref('dim_location') }} as location
    on inventory.location_key = location.location_key
cross join calendar_month
left join occupied
    on inventory.location_key = occupied.location_key
    and calendar_month.month_start_date = occupied.month_start_date
