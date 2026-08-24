select
    md5(tenant_id) as tenant_key,
    tenant_id,
    full_name,
    email
from {{ ref('stg_tenants') }}
