{% macro normalize_status(column_name) %}
    upper(trim({{ column_name }}))
{% endmacro %}