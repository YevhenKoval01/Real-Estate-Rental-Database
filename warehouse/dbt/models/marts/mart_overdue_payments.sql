select
    payment.payment_key,
    payment.payment_id,
    payment.rental_agreement_key,
    payment.property_key,
    payment.location_key,
    location.city,
    payment.due_date,
    payment.payment_date,
    payment.amount,
    payment.days_overdue,
    payment.status
from {{ ref('fact_payment') }} as payment
inner join {{ ref('dim_location') }} as location
    on payment.location_key = location.location_key
where payment.is_overdue
