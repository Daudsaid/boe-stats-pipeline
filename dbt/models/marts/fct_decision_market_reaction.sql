{#- How markets moved around each Bank Rate change.

    * Market window: last close before the effective date vs the close
      {{ var('reaction_days', 5) }} business days later (row offsets on the
      daily table, so weekends/holidays are skipped naturally).
    * Mortgage window: quoted 2y fixed (75% LTV) in the month before the
      change vs three months after. -#}

{%- set n = var('reaction_days', 5) -%}

with daily as (
    select
        observed_on,
        gilt_10y,
        gbp_usd,
        row_number() over (order by observed_on) as day_idx
    from {{ ref('int_daily_rates_wide') }}
    where gilt_10y is not null and gbp_usd is not null
),

decisions as (
    select * from {{ ref('fct_bank_rate_decisions') }}
),

anchored as (
    -- last trading day strictly before the change takes effect
    select decisions.*, before.day_idx as before_idx
    from decisions
    asof left join daily as before
        on decisions.effective_date > before.observed_on
),

mortgages as (
    select month, mortgage_2y_75ltv
    from {{ ref('int_monthly_series_wide') }}
)

select
    anchored.decision_id,
    anchored.effective_date,
    anchored.direction,
    anchored.change_bps,

    before.observed_on                                   as baseline_date,
    after.observed_on                                    as reaction_date,
    round((after.gilt_10y - before.gilt_10y) * 100, 2)   as gilt_10y_move_bps,
    round((after.gbp_usd / before.gbp_usd - 1) * 100, 4) as gbp_usd_move_pct,

    m_before.mortgage_2y_75ltv                           as mortgage_2y_75ltv_before,
    m_after.mortgage_2y_75ltv                            as mortgage_2y_75ltv_after_3m,
    round((m_after.mortgage_2y_75ltv - m_before.mortgage_2y_75ltv) * 100, 2)
                                                         as mortgage_move_3m_bps
from anchored
left join daily as before on before.day_idx = anchored.before_idx
left join daily as after  on after.day_idx  = anchored.before_idx + {{ n }}
left join mortgages as m_before
    on m_before.month = date_trunc('month', anchored.effective_date - interval 1 month)::date
left join mortgages as m_after
    on m_after.month = date_trunc('month', anchored.effective_date + interval 3 month)::date
