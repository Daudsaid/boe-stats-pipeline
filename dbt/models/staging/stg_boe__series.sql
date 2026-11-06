select
    code        as series_code,
    name        as series_name,
    description,
    frequency,
    unit,
    category
from {{ source('boe', 'series') }}
