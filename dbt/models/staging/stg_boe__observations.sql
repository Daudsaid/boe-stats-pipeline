with observations as (
    select * from {{ source('boe', 'observations') }}
),

series as (
    select * from {{ source('boe', 'series') }}
)

select
    observations.series_code,
    series.name                         as series_name,
    series.category,
    series.frequency,
    series.unit,
    observations.date                   as observed_on,
    cast(observations.value as double)  as value,
    to_timestamp(cast(observations._dlt_load_id as double)) as loaded_at
from observations
inner join series on observations.series_code = series.code
