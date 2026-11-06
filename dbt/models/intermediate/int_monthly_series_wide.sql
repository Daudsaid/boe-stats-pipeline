{#- One row per calendar month. Daily series are summarised two ways:
    end-of-month (last published value) and monthly average. Monthly series
    are taken as published. -#}

with daily as (
    select
        date_trunc('month', observed_on)::date as month,
        series_name,
        avg(value)                             as month_avg,
        arg_max(value, observed_on)            as month_end
    from {{ ref('stg_boe__observations') }}
    where frequency = 'daily'
    group by all
),

monthly as (
    select
        date_trunc('month', observed_on)::date as month,
        series_name,
        value
    from {{ ref('stg_boe__observations') }}
    where frequency = 'monthly'
),

months as (
    select distinct month from daily
    union
    select distinct month from monthly
)

select
    months.month,
    {%- for name in ['bank_rate', 'sonia', 'gilt_5y', 'gilt_10y', 'gilt_20y', 'gbp_usd', 'gbp_eur'] %}
    max(daily.month_end) filter (where daily.series_name = '{{ name }}') as {{ name }}_eom,
    max(daily.month_avg) filter (where daily.series_name = '{{ name }}') as {{ name }}_avg,
    {%- endfor %}
    {%- for name in ['mortgage_2y_75ltv', 'mortgage_2y_90ltv', 'm4_outstanding', 'm4_growth_12m'] %}
    max(monthly.value) filter (where monthly.series_name = '{{ name }}') as {{ name }}{{ ',' if not loop.last }}
    {%- endfor %}
from months
left join daily   on months.month = daily.month
left join monthly on months.month = monthly.month
group by months.month
