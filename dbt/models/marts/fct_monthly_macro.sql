{#- Month-grain macro panel: policy, market, mortgage and money data aligned.
    Quoted mortgage rates are monthly averages, so the mortgage spread is
    measured against the monthly-average Bank Rate, not month-end. -#}

with monthly as (
    select * from {{ ref('int_monthly_series_wide') }}
)

select
    month,
    bank_rate_eom,
    bank_rate_avg,
    sonia_avg,
    gilt_10y_eom,
    gilt_10y_avg,
    gbp_usd_eom,
    gbp_eur_eom,
    round((gbp_usd_eom / lag(gbp_usd_eom) over (order by month) - 1) * 100, 4) as gbp_usd_mom_pct,
    round((gbp_eur_eom / lag(gbp_eur_eom) over (order by month) - 1) * 100, 4) as gbp_eur_mom_pct,
    mortgage_2y_75ltv,
    mortgage_2y_90ltv,
    round((mortgage_2y_75ltv - bank_rate_avg) * 100, 2)     as mortgage_75ltv_spread_bps,
    round((mortgage_2y_90ltv - mortgage_2y_75ltv) * 100, 2) as ltv_premium_90_vs_75_bps,
    m4_outstanding,
    m4_growth_12m
from monthly
