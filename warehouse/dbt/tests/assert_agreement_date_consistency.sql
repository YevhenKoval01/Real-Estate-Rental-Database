select agreement_id
from {{ ref('fact_rental_agreement') }}
where end_date < start_date
    or agreement_days <= 0
