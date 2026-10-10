{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

select
    o.order_id,
    o.customer_id,
    o.warehouse_id,
    o.status,
    s.status_group,
    o.subtotal_amount,
    o.tax_amount,
    o.handling_amount,
    o.discount_amount,
    o.total_amount,
    o.created_at,
    o.updated_at

from {{ ref('int_orders') }} o

left join {{ ref('order_status_mapping') }} s
    on o.status = s.status

{% if is_incremental() %}

where o.updated_at > (
    select max(updated_at)
    from {{ this }}
)

{% endif %}