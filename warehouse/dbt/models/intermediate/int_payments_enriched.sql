select
    payment.payment_id,
    payment.agreement_id,
    agreement.property_id,
    agreement.tenant_id,
    agreement.owner_id,
    agreement.location_id,
    payment.due_date,
    payment.payment_date,
    payment.amount,
    payment.status,
    agreement.city,
    agreement.region,
    agreement.size_sqm,
    agreement.monthly_rent
from {{ ref('stg_payments') }} as payment
inner join {{ ref('int_agreements_enriched') }} as agreement
    on payment.agreement_id = agreement.agreement_id
