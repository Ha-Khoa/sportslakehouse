{#
  dbt's default builds schema names like "main_silver" (target schema + custom schema).
  We want the layer names exactly: staging, silver, gold. So use the custom name as it is.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
