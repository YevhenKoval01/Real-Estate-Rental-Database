select
    payment.location_key,
    location.city,
    location.region,
    date_trunc('month', payment.payment_date)::date as revenue_month,
    count(*) as paid_payment_count,
    sum(payment.amount) as rental_revenue
from {{ ref('fact_payment') }} as payment
inner join {{ ref('dim_location') }} as location
    on payment.location_key = location.location_key
where payment.status = 'PAID'
group by
    payment.location_key,
    location.city,
    location.region,
    date_trunc('month', payment.payment_date)::date
