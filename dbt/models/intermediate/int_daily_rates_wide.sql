{#- One row per business day with every daily series as a column.
    Series that did not publish on a given day are null (e.g. FX on a
    UK-only holiday); downstream models decide whether to carry forward. -#}

{%- set daily_series = ['bank_rate', 'sonia', 'gilt_5y', 'gilt_10y', 'gilt_20y', 'gbp_usd', 'gbp_eur'] -%}

select
    observed_on,
    {%- for name in daily_series %}
    max(value) filter (where series_name = '{{ name }}') as {{ name }}{{ ',' if not loop.last }}
    {%- endfor %}
from {{ ref('stg_boe__observations') }}
where frequency = 'daily'
group by observed_on
