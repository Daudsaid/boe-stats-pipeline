with source as (
    select
        date,
        value as m4_gbp_millions,
        series_code,
        extracted_at
    from raw_m4_money_supply
)

select
    date,
    m4_gbp_millions,
    m4_gbp_millions - lag(m4_gbp_millions) over (order by date) as m4_monthly_change,
    round(
        (m4_gbp_millions - lag(m4_gbp_millions) over (order by date)) / nullif(lag(m4_gbp_millions) over (order by date), 0) * 100
    , 4) as m4_growth_pct,
    series_code,
    extracted_at
from source
order by date
