select location_key, month_start_date, occupancy_rate
from {{ ref('mart_occupancy') }}
where occupancy_rate < 0
    or occupancy_rate > 1
