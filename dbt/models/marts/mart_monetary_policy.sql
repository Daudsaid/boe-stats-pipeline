with base as (
    select
        date,
        base_rate_pct,
        rate_change,
        rate_direction
    from {{ ref('stg_base_rate') }}
),

mortgage as (
    select
        date,
        mortgage_rate_pct,
        rate_change as mortgage_rate_change
    from {{ ref('stg_mortgage_rate') }}
),

m4 as (
    select
        date,
        m4_gbp_millions,
        m4_monthly_change
    from {{ ref('stg_m4_money_supply') }}
)

select
    base.date,
    base.base_rate_pct,
    base.rate_change        as base_rate_change,
    base.rate_direction,
    mortgage.mortgage_rate_pct,
    mortgage.mortgage_rate_change,
    round(mortgage.mortgage_rate_pct - base.base_rate_pct, 4) as mortgage_base_spread,
    m4.m4_gbp_millions,
    m4.m4_monthly_change
from base
left join mortgage on base.date = mortgage.date
left join m4 on base.date = m4.date
order by base.date
