with bounds as (
    select
        least(min(start_date), min(end_date)) as minimum_date,
        greatest(max(start_date), max(end_date)) as maximum_date
    from {{ ref('stg_rental_agreements') }}
),
date_spine as (
    select generated_date::date as date_day
    from bounds
    cross join lateral generate_series(
        minimum_date::timestamp,
        maximum_date::timestamp,
        interval '1 day'
    ) as generated_date
)
select
    to_char(date_day, 'YYYYMMDD')::integer as date_key,
    date_day,
    extract(year from date_day)::integer as year_number,
    extract(quarter from date_day)::integer as quarter_number,
    extract(month from date_day)::integer as month_number,
    to_char(date_day, 'Month') as month_name,
    extract(isodow from date_day)::integer as iso_weekday_number,
    to_char(date_day, 'Day') as weekday_name,
    (extract(isodow from date_day) in (6, 7)) as is_weekend,
    date_trunc('month', date_day)::date as month_start_date
from date_spine
