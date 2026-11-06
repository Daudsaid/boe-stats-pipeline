{#- Daily sterling curve: policy rate, overnight rate and gilt par yields,
    with the spreads people actually watch. Days missing any curve point are
    dropped rather than forward-filled, so spreads are always same-day. -#}

select
    observed_on,
    bank_rate,
    sonia,
    gilt_5y,
    gilt_10y,
    gilt_20y,
    round((sonia    - bank_rate) * 100, 2) as sonia_vs_bank_rate_bps,
    round((gilt_10y - gilt_5y)   * 100, 2) as slope_10y_5y_bps,
    round((gilt_20y - gilt_5y)   * 100, 2) as slope_20y_5y_bps,
    round((gilt_10y - bank_rate) * 100, 2) as term_spread_10y_bank_bps,
    gilt_10y < bank_rate                   as is_10y_below_bank_rate
from {{ ref('int_daily_rates_wide') }}
where bank_rate is not null
  and gilt_5y   is not null
  and gilt_10y  is not null
  and gilt_20y  is not null
