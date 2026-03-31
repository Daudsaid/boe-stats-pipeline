with usd as (
    select date, value as gbp_usd, extracted_at
    from raw_gbp_usd
),
eur as (
    select date, value as gbp_eur
    from raw_gbp_eur
)

select
    usd.date,
    usd.gbp_usd,
    eur.gbp_eur,
    round((usd.gbp_usd - lag(usd.gbp_usd) over (order by usd.date)) / lag(usd.gbp_usd) over (order by usd.date) * 100, 4) as usd_monthly_change_pct,
    round((eur.gbp_eur - lag(eur.gbp_eur) over (order by usd.date)) / lag(eur.gbp_eur) over (order by usd.date) * 100, 4) as eur_monthly_change_pct,
    usd.extracted_at
from usd
join eur on usd.date = eur.date
order by usd.date
