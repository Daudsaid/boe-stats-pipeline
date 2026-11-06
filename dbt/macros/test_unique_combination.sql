{#- Generic test: the given columns are unique together. Avoids a dbt_utils
    dependency for a single test. -#}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
