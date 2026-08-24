select
    md5(owner_id) as owner_key,
    owner_id,
    full_name,
    email
from {{ ref('stg_owners') }}
