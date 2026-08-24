select
    md5(payment.payment_id) as payment_key,
    payment.payment_id,
    md5(payment.agreement_id) as rental_agreement_key,
    property.property_key,
    property.location_key,
    tenant.tenant_key,
    to_char(payment.due_date, 'YYYYMMDD')::integer as due_date_key,
    to_char(payment.payment_date, 'YYYYMMDD')::integer as payment_date_key,
    payment.due_date,
    payment.payment_date,
    payment.amount,
    payment.status,
    greatest(payment.payment_date - payment.due_date, 0) as days_overdue,
    (payment.payment_date > payment.due_date or payment.status = 'OVERDUE') as is_overdue
from {{ ref('stg_payments') }} as payment
inner join {{ ref('stg_rental_agreements') }} as agreement
    on payment.agreement_id = agreement.agreement_id
inner join {{ ref('dim_property') }} as property
    on agreement.property_id = property.property_id
inner join {{ ref('dim_tenant') }} as tenant
    on agreement.tenant_id = tenant.tenant_id
