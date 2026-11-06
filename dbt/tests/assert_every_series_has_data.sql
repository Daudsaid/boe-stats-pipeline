-- Every series in the registry must have loaded at least one observation.
-- Catches a renamed/discontinued BoE series code that returns nothing.
select series.series_code, series.series_name
from {{ ref('stg_boe__series') }} as series
left join {{ ref('stg_boe__observations') }} as obs using (series_code)
group by all
having count(obs.observed_on) = 0
