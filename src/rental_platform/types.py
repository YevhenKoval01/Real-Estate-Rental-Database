type Record = dict[str, object]
type Dataset = dict[str, list[Record]]

ENTITY_ORDER = (
    "locations",
    "owners",
    "tenants",
    "properties",
    "rental_agreements",
    "payments",
)
