{% macro order_total(subtotal, tax, handling, discount) %}
    {{ subtotal }}
    + {{ tax }}
    + {{ handling }}
    - {{ discount }}
{% endmacro %}
