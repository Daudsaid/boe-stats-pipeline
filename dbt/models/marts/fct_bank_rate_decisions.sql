{#- Every change to Official Bank Rate, derived from the daily series.
    A "decision" here is a change in the published rate; MPC meetings that
    held rates leave no trace in the daily series and are not included. -#}

with bank_rate as (
    select observed_on, value as rate
    from {{ ref('stg_boe__observations') }}
    where series_name = 'bank_rate'
),

with_previous as (
    select
        observed_on,
        rate,
        lag(rate) over (order by observed_on) as previous_rate
    from bank_rate
),

changes as (
    select
        observed_on                                   as effective_date,
        previous_rate,
        rate                                          as new_rate,
        round((rate - previous_rate) * 100)::integer  as change_bps
    from with_previous
    where previous_rate is not null
      and rate <> previous_rate
)

select
    row_number() over (order by effective_date)::integer             as decision_id,
    effective_date,
    previous_rate,
    new_rate,
    change_bps,
    case when change_bps > 0 then 'hike' else 'cut' end               as direction,
    (effective_date - lag(effective_date) over (order by effective_date))::integer
                                                                      as days_since_previous_change
from changes
