with fx as (
    select
        date,
        gbp_usd,
        gbp_eur,
        usd_monthly_change_pct,
        eur_monthly_change_pct
    from {{ ref('stg_exchange_rates') }}
),

base as (
    select
        date,
        base_rate_pct,
        rate_direction
    from {{ ref('stg_base_rate') }}
)

select
    fx.date,
    fx.gbp_usd,
    fx.gbp_eur,
    fx.usd_monthly_change_pct,
    fx.eur_monthly_change_pct,
    base.base_rate_pct,
    base.rate_direction
from fx
left join base on fx.date = base.date
order by fx.date
