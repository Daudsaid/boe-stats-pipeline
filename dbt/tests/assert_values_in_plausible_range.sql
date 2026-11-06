-- Guards against unit/scale mistakes (e.g. a rate loaded as 475 instead of 4.75)
-- and against a wrong series code silently returning a different measure.
select series_code, series_name, unit, observed_on, value
from {{ ref('stg_boe__observations') }}
where
    (unit = 'percent' and series_name <> 'm4_growth_12m' and (value < -1 or value > 25))
    or (series_name = 'm4_growth_12m' and (value < -20 or value > 40))
    or (unit in ('usd_per_gbp', 'eur_per_gbp') and (value < 0.5 or value > 3))
    or (unit = 'gbp_millions' and value <= 0)
