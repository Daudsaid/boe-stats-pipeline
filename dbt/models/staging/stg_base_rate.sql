with source as (
    select
        date,
        value as base_rate_pct,
        series_code,
        extracted_at
    from {{ source('boe', 'raw_base_rate') }}
)

select
    date,
    base_rate_pct,
    base_rate_pct - lag(base_rate_pct) over (order by date) as rate_change,
    case
        when base_rate_pct > lag(base_rate_pct) over (order by date) then 'hike'
        when base_rate_pct < lag(base_rate_pct) over (order by date) then 'cut'
        else 'hold'
    end as rate_direction,
    series_code,
    extracted_at
from source
order by date