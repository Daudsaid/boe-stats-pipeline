select series_code, observed_on
from {{ ref('stg_boe__observations') }}
where observed_on > current_date
