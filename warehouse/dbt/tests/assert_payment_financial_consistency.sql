select payment_id
from {{ ref('fact_payment') }}
where amount < 0
    or days_overdue < 0
    or (not is_overdue and days_overdue <> 0)
