{{ config(severity='warn', warn_if='>3') }}
-- Riskier (90% LTV) fixed mortgages should cost more than 75% LTV ones.
-- A handful of months can invert, but many inversions mean a series code points
-- at the wrong product (this caught IUMB479, a tracker, posing as a 2y fix).
select month, mortgage_2y_75ltv, mortgage_2y_90ltv
from {{ ref('fct_monthly_macro') }}
where mortgage_2y_90ltv < mortgage_2y_75ltv - 0.25
