{% snapshot orders_snapshot %}

{{
    config(
        target_schema='novacart',
        unique_key='order_id',
        strategy='timestamp',
        updated_at='updated_at',
        snapshot_meta_column_names={
            'dbt_valid_from': 'dbt_valid_from',
            'dbt_valid_to': 'dbt_valid_to'
        }
    )
}}

select
    order_id,
    customer_id,
    warehouse_id,
    status,
    subtotal_amount,
    tax_amount,
    handling_amount,
    discount_amount,
    total_amount,
    created_at,
    updated_at

from {{ source('app', 'orders') }}

{% endsnapshot %}