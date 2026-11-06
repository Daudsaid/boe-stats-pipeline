with source as (
    select
        date,
        value as mortgage_rate_pct,
        series_code,
        extracted_at
    from {{ source('boe', 'raw_mortgage_rate') }}
)

select
    date,
    mortgage_rate_pct,
    mortgage_rate_pct - lag(mortgage_rate_pct) over (order by date) as rate_change,
    series_code,
    extracted_at
from source
order by date